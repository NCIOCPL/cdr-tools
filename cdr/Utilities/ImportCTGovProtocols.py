#----------------------------------------------------------------------
#
# $Id: ImportCTGovProtocols.py,v 1.9 2006-05-18 18:53:49 bkline Exp $
#
# $Log: not supported by cvs2svn $
# Revision 1.8  2005/09/19 19:23:59  bkline
# Modified logic to create publishable version even if significant changes
# are detected.
#
# Revision 1.7  2004/04/02 19:16:49  bkline
# Implemented modification for request #1172 (special handling for
# terminated protocols).
#
# Revision 1.6  2004/03/30 22:12:37  bkline
# Fixed typo in PDQ sponsorship mapping value.
#
# Revision 1.5  2004/03/30 16:52:57  bkline
# Added mapping for WARREN GRANT MAGNUSON CLINICAL CENTER (request #1159).
#
# Revision 1.4  2004/03/22 15:38:40  bkline
# Enhancements for request #1150 (PDQ sponsorship handling changes).
#
# Revision 1.3  2003/12/16 13:28:58  bkline
# Improved detection and elimination of blank Para and ListItem elements.
#
# Revision 1.2  2003/12/14 19:07:06  bkline
# Final versions for promotion to production system.
#
# Revision 1.1  2003/11/05 16:25:19  bkline
# Batch job for adding or updating CTGovProtocols to/in the CDR.
#
#----------------------------------------------------------------------
import cdr, cdrdb, sys, xml.sax, re, cdrcgi

class Flags:
    def __init__(self):
        self.clear()
    def clear(self):
        self.isNew = 'N'
        self.needsReview = 'N'
        self.pubVersionCreated = 'N'
        self.locked = 0
        self.terminated = 0

class CTGovHandler(xml.sax.handler.ContentHandler):
    def __init__(self, flags):
        self.doc      = u""
        self.para     = u""
        self.inPara   = 0
        self.flags    = flags
        self.inStatus = 0
        self.status   = u""
    def startDocument(self):
        self.doc = u"<?xml version='1.0'?>\n"
    def startElement(self, name, attributes):
        if name == u'Para':
            self.para   = u""
            self.inPara = 1
        else:
            if name == 'OverallStatus':
                self.status = u""
                self.inStatus = 1
            self.doc += u"<%s" % name
            for attrName in attributes.getNames():
                val = xml.sax.saxutils.quoteattr(attributes.getValue(attrName))
                self.doc += u" %s=%s" % (attrName, val)
            self.doc += u">"
    def endElement(self, name):
        if name == 'Para':
            self.doc += self.parsePara()
            self.inPara = 0
            self.para = u""
        else:
            if name == 'OverallStatus':
                print "STATUS: ", self.status
                if self.status.upper().strip() in ("WITHDRAWN", "TERMINATED"):
                    self.flags.terminated = 1
                self.inStatus = 0
            self.doc += "</%s>" % name
    def characters(self, content):
        if self.inPara:
            self.para += xml.sax.saxutils.escape(content)
        else:
            text = xml.sax.saxutils.escape(content)
            if self.inStatus:
                self.status += text
            self.doc += text
    def processingInstruction(self, target, data):
        self.doc += "<?%s %s?>" % (target, data)
    def parsePara(self):
        #self.para = self.para.strip()
        self.para = self.para.replace(u"\r", "")
        if not self.para:
            return u"<Para/>\n"
        result = u""
        chunks = re.split(u"\n\n+", self.para)
        for chunk in chunks:
            if re.match(r"\s+-\s", chunk):
                items = u""
                for item in re.split(r"\n\s+-\s", u"dummy\n" + chunk)[1:]:
                    i = item.strip()
                    if i:
                        items += u"<ListItem>%s</ListItem>\n" % i
                if items:
                    result += u"<ItemizedList>\n%s</ItemizedList>\n" % items
            else:
                para = chunk.strip()
                if para:
                    result += u"<Para>%s</Para>\n" % para
        return result

#----------------------------------------------------------------------
# Gather a list of email recipients for reports.
#----------------------------------------------------------------------
def getEmailRecipients(cursor, includeDeveloper = False):
    developer = '***REMOVED***'
    try:
        cursor.execute("""\
            SELECT u.email
              FROM usr u
              JOIN grp_usr gu
                ON gu.usr = u.id
              JOIN grp g
                ON g.id = gu.grp
             WHERE g.name = 'CTGov Publishers'
               AND u.expired IS NULL
               AND u.email IS NOT NULL
               AND u.email <> ''""")
        recips = [row[0] for row in cursor.fetchall()]
        if includeDeveloper and developer not in recips:
            recips.append(developer)
        return recips
    except:
        if includeDeveloper:
            return [developer]

def parseParas(doc):
    parser.doc = u""
    xml.sax.parseString(doc, parser)
    return parser.doc

def log(msg, cdrErrors = None, tback = 0):
    if cdrErrors:
        errors = cdr.getErrors(cdrErrors, asSequence = 1)
        if not errors:
            cdr.logwrite(msg, LOGFILE, tback)
        elif len(errors) == 1:
            cdr.logwrite("%s: %s" % (msg, errors[0]), LOGFILE, tback)
        else:
            cdr.logwrite(msg, LOGFILE, tback)
            cdr.logwrite(errors, LOGFILE)
    else:
        cdr.logwrite(msg, LOGFILE, tback)

def checkResponse(resp):
    if not resp[0]:
        errors = cdr.getErrors(resp[1], errorsExpected = 1, asSequence = 1)
        raise Exception(errors)
    if resp[1]:
        errors = cdr.getErrors(resp[1], errorsExpected = 0, asSequence = 1)
        return errors

def extractDocSubset(cdrId, docVer = None):
    response = cdr.filterDoc(session,
                          ['name:Extract Significant CTGovProtocol Elements'],
                             cdrId, docVer = docVer)
    if not response[0]:
        raise Exception(response[1])
    return response[0]

def hasMajorDiffs(cdrId, version, newSubset):
    oldSubset = extractDocSubset(cdrId, version)
    return newSubset != oldSubset
    
def mergeVersion(newDoc, cdrId, docObject, docVer):
    element  = ""
    response = cdr.getDoc('guest', cdrId, version = docVer)
    errors   = cdr.getErrors(response, errorsExpected = 0, asSequence = 1)
    if errors:
        raise Exception(errors)
    startTag = "<PDQIndexing"
    endTag   = "</PDQIndexing>"
    begin    = response.find(startTag)
    while begin != -1 and response[begin + len(startTag)] not in "> \n\r\t":
        begin = response.find(startTag, begin + 1)
    if begin != -1:
        end = response.find(endTag, begin)
        if end != -1:
            element = response[begin:end + len(endTag)]
    docObject.xml = newDoc.replace('@@PDQIndexing@@', element)
    return str(docObject)

def mergeChanges(cdrId, newDoc, flags):

    response = cdr.getDoc(session, cdrId, checkout = 'Y', getObject = 1)
    errors   = cdr.getErrors(response, errorsExpected = 0, asSequence = 1)
    if errors:
        flags.locked = 1
        cursor.execute("""\
        INSERT INTO ctgov_import_event (job, nlm_id, locked, new)
             VALUES (?, ?, 'Y', 'N')""", (job, nlmId))
        conn.commit()
        raise Exception(errors)
    docObject = response
    originalXml = docObject.xml
    response = cdr.filterDoc(session,
                          ['name:Extract Significant CTGovProtocol Elements'],
                             doc = newDoc)
    if not response[0]:
        raise Exception(response[1])
    newSubset = response[0]
    lastAny, lastPub, isChanged = cdr.lastVersions(session, cdrId)
    newCwd   = mergeVersion(newDoc, cdrId, docObject, "Current")

    # Save the old CWD as a version if appropriate.
    if isChanged == 'Y':
        comment = 'ImportCTGovProtocols: preserving current working doc'
        #print str(docObject)
        response = cdr.repDoc(session, doc = str(docObject), ver = 'Y',
                              reason = comment, comment = comment,
                              showWarnings = 1, verPublishable = 'N')
        checkResponse(response)


    # New requirement (#1172): special handling for terminated protocols.
    if flags.terminated:
        print "handling terminated doc"
        comment  = 'ImportCTGovProtocols: versioning terminated protocol'
        response = cdr.repDoc(session, doc = newCwd, ver = 'Y',
                              verPublishable = 'N',
                              reason = comment, comment = comment,
                              showWarnings = 1, activeStatus = 'I')
        checkResponse(response)

    # Has a publishable version ever been saved for this document?
    elif lastPub != -1:

        # If the differences are not significant, create a new pub. ver.
        if hasMajorDiffs(cdrId, lastPub, newSubset):
            flags.needsReview = 'Y'
        newPubVer = mergeVersion(newDoc, cdrId, docObject, lastPub)
        comment = 'ImportCTGovProtocols: creating new publishable version'
        response = cdr.repDoc(session, doc = newPubVer, ver = 'Y',
                              verPublishable = 'Y', val = 'Y',
                              reason = comment, comment = comment,
                              showWarnings = 1)
        errs = checkResponse(response)
        flags.pubVersionCreated = errs and 'F' or 'Y'
        if errs:
            cdr.logwrite("%s: %s" % (cdrId, errs[0]), LOGFILE)

    elif hasMajorDiffs(cdrId, None, newSubset):
        flags.needsReview = 'Y'
        
    # Create a new CWD from the one we found updated with NLM's changes.
    comment  = 'ImportCTGovProtocols: creating new CWD'
    response = cdr.repDoc(session, doc = newCwd,
                          reason = comment, comment = comment,
                          showWarnings = 1,
                          activeStatus = flags.terminated and 'I' or None)
    checkResponse(response)

#----------------------------------------------------------------------
# Plug in PDQ sponsorship information if appropriate.
#----------------------------------------------------------------------
pdqSponsorshipMap = {
    "NATIONAL CENTER FOR COMPLEMENTARY AND ALTERNATIVE MEDICINE"      :"NCCAM",
    "NATIONAL HEART, LUNG, AND BLOOOD INSTITUTE"                      :"NHLBI",
    "NATIONAL INSTITUTE OF ALLERGY AND INFECTIOUS DISEASES"           :"NIAID",
    "NATIONAL INSTITUTE OF ARTHRITIS AND MUSCULOSKELETAL DISEASES"    :"NIAMS",
    "NATIONAL INSTITUTE OF DENTAL AND CRANIOFACIAL RESEARCH"          :"NIDCR",
    "NATIONAL INSTITUTE OF DIABETES AND DIGESTIVE AND KIDNEY DISEASES":"NIDDK",
    "NATIONAL INSTITUTE OF NEUROLOGICAL DISORDERS AND STROKE"         :"NINDS",
    "NATIONAL EYE INSTITUTE"                                          :"NEI",
    "NATIONAL INSTITUTE ON AGING"                                     :"NIA",
    "NATIONAL INSTITUTE OF CHILD HEALTH AND HUMAN DEVELOPMENT"        :"NICHD",
    "NATIONAL INSTITUTE ON DEAFNESS AND OTHER COMMUNICATION DISORDERS":"NIDCD",
    "NATIONAL INSTITUTE OF ENVIRONMENTAL HEALTH SCIENCES"             :"NIEHS",
    "NATIONAL CENTER FOR RESEARCH RESOURCES"                          :"NCRR",
    "NATIONAL HUMAN GENOME RESEARCH INSTITUTE"                        :"NHGRI",
    "NATIONAL INSTITUTE OF MENTAL HEALTH"                             :"NIMH",
    "NATIONAL INSTITUTE OF GENERAL MEDICAL SCIENCES"                  :"NIGMS",
    "NATIONAL INSTITUTE OF NURSING RESEARCH"                          :"NINR",
    "WARREN GRANT MAGNUSON CLINICAL CENTER"                       :"NIH WGMCC"
    }
def fixPdqSponsorship(doc):
    pdqSponsorship = ""
    docType = None
    match = spPatt.search(doc)
    if match:
        digits = re.sub(r"[^\d]", "", match.group(1))
        if digits:
            docId  = int(digits)
            cursor.execute("""\
                SELECT t.name
                  FROM doc_type t
                  JOIN document d
                    ON d.doc_type = t.id
                 WHERE d.id = ?""", docId)
            rows = cursor.fetchall()
            if rows:
                docType = rows[0][0]
                cursor.execute("""\
                    SELECT value
                      FROM query_term
                     WHERE path = '/Organization/OrganizationType'
                       AND doc_id = ?""", docId)
                rows = cursor.fetchall()
            if docType == "Person":
                pdqSponsorship = "Other"
            elif docType and rows:
                orgType = rows[0][0].strip().upper()
                print "orgType: %s" % orgType
                if orgType == "PHARMACEUTICAL/BIOMEDICAL":
                    pdqSponsorship = "Pharmaceutical/Industry"
                elif orgType == "NCI INSTITUTE, DIVISION, OR OFFICE":
                    pdqSponsorship = "NCI"
                elif orgType == "NIH INSTITUTE, CENTER, OR DIVISION":
                    pdqSponsorship = "Other"
                    cursor.execute("""\
                    SELECT value
                      FROM query_term
                     WHERE path = '/Organization/OrganizationNameInformation'
                                + '/OfficialName/Name'
                       AND doc_id = ?""", docId)
                    rows = cursor.fetchall()
                    if rows:
                        orgName = rows[0][0].strip().upper()
                        print "orgName: %s" % orgName
                        if pdqSponsorshipMap.has_key(orgName):
                            pdqSponsorship = pdqSponsorshipMap[orgName]
                else:
                    pdqSponsorship = "Other"
    if pdqSponsorship:
        pdqSponsorship = ("<PDQSponsorship>%s</PDQSponsorship>" %
                          pdqSponsorship)
        print pdqSponsorship
        return spPatt.sub(pdqSponsorship, doc)
    return doc

#----------------------------------------------------------------------
# Module-scoped data.
#----------------------------------------------------------------------
LOGFILE = cdr.DEFAULT_LOGDIR + "/CTGovImport.log"
flags   = Flags()
parser  = CTGovHandler(flags)
conn    = cdrdb.connect()
cursor  = conn.cursor()
session = cdr.login('CTGovImport', '***REMOVED***')
errors  = cdr.getErrors(session, errorsExpected = 0, asSequence = 1)
spPatt  = re.compile("@@PDQSPONSORSHIP=([^@]*)@@")
if errors:
    cdr.logwrite("Login failure", session)
    sys.stderr.write("Login failure: %s" % str(errors))
    sys.exit(1)
cursor.execute("SELECT id FROM ctgov_disposition WHERE name = 'imported'")
importedDisposition = cursor.fetchall()[0][0]
cursor.execute("""\
    SELECT c.nlm_id, c.cdr_id
      FROM ctgov_import c
      JOIN ctgov_disposition d
        ON d.id = c.disposition
     WHERE d.name = 'import requested'""")
rows = cursor.fetchall()
cursor.execute("INSERT into ctgov_import_job (dt) VALUES (GETDATE())")
conn.commit()
cursor.execute("SELECT @@IDENTITY")
job = cursor.fetchone()[0]
failures = []
for nlmId, cdrId in rows:
    print nlmId, cdrId
    flags.clear()
    cursor.execute("SELECT xml FROM ctgov_import WHERE nlm_id = ?", nlmId)
    doc = cursor.fetchone()[0]
    parms = [['newDoc', cdrId and 'N' or 'Y']]
    resp = cdr.filterDoc('guest', ['name:Import CTGovProtocol'], doc = doc,
                         parm = parms)
    if type(resp) in (type(""), type(u"")):
        failures.append("Failure converting %s" % nlmId)
        log("Failure converting %s" % nlmId, resp)
        continue

    doc = parseParas(resp[0])
    doc = fixPdqSponsorship(doc)

    #------------------------------------------------------------------
    # Add new doc.
    #------------------------------------------------------------------
    if not cdrId:
        flags.isNew = 'Y'
        comment = ('ImportCTGovProtocols: '
                   'Adding imported CTGovProtocol document')
        resp = cdr.addDoc(session, doc = """\
<CdrDoc Type='CTGovProtocol'>
 <CdrDocCtl>
  <DocComment>%s</DocComment>
 </CdrDocCtl>
 <CdrDocXml><![CDATA[%s]]></CdrDocXml>
</CdrDoc>
""" % (comment, doc.encode('utf-8')), showWarnings = 1,
                          reason = comment, ver = "Y", val = "N",
                          verPublishable = 'N')
        if not resp[0]:
            log("Failure adding %s" % nlmId, resp[1])
            failures.append("Failure adding %s" % nlmId)
        else:
            cdr.unlock(session, resp[0],
                       reason = 'ImportCTGovProtocols: '
                                'Unlocking imported CTGovProtocol doc')
            digits = re.sub(r'[^\d]', '', resp[0])
            cdrId = int(digits)
            cursor.execute("""\
            UPDATE ctgov_import
               SET disposition = ?,
                   dt = GETDATE(),
                   cdr_id = ?
             WHERE nlm_id = ?""", (importedDisposition, cdrId, nlmId))
            conn.commit()
            log("Added %s as %s" % (nlmId, resp[0]))

    #------------------------------------------------------------------
    # Merge changes into existing doc.
    #------------------------------------------------------------------
    else:
        try:
            mergeChanges("CDR%d" % cdrId, doc.encode('utf-8'), flags)
            cursor.execute("""\
            UPDATE ctgov_import
               SET disposition = ?,
                   dt = GETDATE()
             WHERE nlm_id = ?""", (importedDisposition, nlmId))
            conn.commit()
        except Exception, info:
            failures.append("Failure merging changes for %s into %s" %
                            (nlmId, cdrId))
            log("Failure merging changes for %s into %s: %s" %
                (nlmId, cdrId, str(info)), tback = (flags.locked == 0))
            #raise
        if not flags.locked:
            cdr.unlock(session, "CDR%d" % cdrId,
                       reason = 'ImportCTGovProtocols: '
                                'Unlocking updated CTGovProtocol doc')
            log("Updated CDR%d from %s" % (cdrId, nlmId))
    if not flags.locked:
        try:
            cursor.execute("""\
 INSERT INTO ctgov_import_event(job, nlm_id, new, needs_review, pub_version)
      VALUES (?, ?, ?, ?, ?)""", (job,
                                  nlmId,
                                  flags.isNew,
                                  flags.needsReview,
                                  flags.pubVersionCreated))
            conn.commit()
        except Exception, info:
            failures.append("Failure recording import event for %s" % nlmId)
            log("Failure recording import event for %s: %s" %
                (nlmId, str(info)))
if failures:
    recips = getEmailRecipients(cursor, True)
    print recips
    recips = ['***REMOVED***']
    body = """\
CT.gov import failures encountered; see logs for more information:

%s
""" % "\n".join(failures)
    subject = "CT.gov import failures"
    sender = "cdr@%s" % cdrcgi.WEBSERVER
    cdr.sendMail(sender, recips, subject, body)
