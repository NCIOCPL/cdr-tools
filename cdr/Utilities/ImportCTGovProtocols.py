#----------------------------------------------------------------------
#
# $Id: ImportCTGovProtocols.py,v 1.3 2003-12-16 13:28:58 bkline Exp $
#
# $Log: not supported by cvs2svn $
# Revision 1.2  2003/12/14 19:07:06  bkline
# Final versions for promotion to production system.
#
# Revision 1.1  2003/11/05 16:25:19  bkline
# Batch job for adding or updating CTGovProtocols to/in the CDR.
#
#----------------------------------------------------------------------
import cdr, cdrdb, sys, xml.sax, re

class Flags:
    def __init__(self):
        self.clear()
    def clear(self):
        self.isNew = 'N'
        self.needsReview = 'N'
        self.pubVersionCreated = 'N'
        self.locked = 0

class CTGovHandler(xml.sax.handler.ContentHandler):
    def __init__(self):
        self.doc    = u""
        self.para   = u""
        self.inPara = 0
    def startDocument(self):
        self.doc = u"<?xml version='1.0'?>\n"
    def startElement(self, name, attributes):
        if name == u'Para':
            self.para   = u""
            self.inPara = 1
        else:
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
            self.doc += "</%s>" % name
    def characters(self, content):
        if self.inPara:
            self.para += xml.sax.saxutils.escape(content)
        else:
            self.doc += xml.sax.saxutils.escape(content)
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

    # Save the old CWD as a version if appropriate.
    if isChanged == 'Y':
        comment = 'ImportCTGovProtocols: preserving current working doc'
        #print str(docObject)
        response = cdr.repDoc(session, doc = str(docObject), ver = 'Y',
                              reason = comment, comment = comment,
                              showWarnings = 1, verPublishable = 'N')
        checkResponse(response)


    # Has a publishable version ever been saved for this document?
    if lastPub != -1:

        # If the differences are not significant, create a new pub. ver.
        if hasMajorDiffs(cdrId, lastPub, newSubset):
            flags.needsReview = 'Y'
        else:
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
    newCwd   = mergeVersion(newDoc, cdrId, docObject, "Current")
    comment  = 'ImportCTGovProtocols: creating new CWD'
    response = cdr.repDoc(session, doc = newCwd,
                          reason = comment, comment = comment,
                          showWarnings = 1)
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
    "NATIONAL INSTITUTE OF GENERAL MEDICAL SCIENCES"                  :"NIGMS"
    }
def fixPdqSponsorship(doc):
    pdqSponsorship = ""
    match = spPatt.search(doc)
    if match:
        digits = re.sub(r"[^\d]", "", match.group(1))
        if digits:
            docId  = int(digits)
            cursor.execute("""\
            SELECT value
              FROM query_term
             WHERE path = '/Organization/OrganizationType'
               AND doc_id = ?""", docId)
            rows = cursor.fetchall()
            if rows:
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
parser  = CTGovHandler()
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
flags = Flags()
for nlmId, cdrId in rows:
    print nlmId, cdrId
    flags.clear()
    cursor.execute("SELECT xml FROM ctgov_import WHERE nlm_id = ?", nlmId)
    doc = cursor.fetchone()[0]
    parms = [['newDoc', cdrId and 'N' or 'Y']]
    resp = cdr.filterDoc('guest', ['name:Import CTGovProtocol'], doc = doc,
                         parm = parms)
    if type(resp) in (type(""), type(u"")):
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
            log("Failure record import event for %s: %s" %
                (nlmId, str(info)))
