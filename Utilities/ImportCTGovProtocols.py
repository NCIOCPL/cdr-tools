#----------------------------------------------------------------------
#
# $Id$
#
# $Log: not supported by cvs2svn $
# Revision 1.20  2009/09/27 19:27:09  bkline
# Modification for issues #4444 and #4634.
#
# Revision 1.19  2008/07/25 15:28:47  bkline
# Fixed a bug in the mergeVersion() function which prevented new information
# from CT.gov from being used in the imported CDR documents.  Documented
# the mergeVersion() and preserveElement() functions.
#
# Revision 1.18  2008/04/17 15:23:23  bkline
# Blocked out mapping for ""NHGRI - CLINICAL GENETHERAPY BRANCH" at
# Kim's request (#4026).
#
# Revision 1.17  2008/04/17 15:15:54  bkline
# Sponsorship Mapping changes requested by Sheri (#4026).
#
# Revision 1.16  2008/03/27 14:48:00  bkline
# Modifications for request #3949 (preserve protocol processing details
# block).
#
# Revision 1.15  2008/01/24 15:02:51  bkline
# Fixed handling of utf-8 characters.
#
# Revision 1.14  2008/01/23 04:28:24  ameyer
# Eliminated saving of a new current working version in those cases
# where a prior save created a CWD that would be identical to the one
# that was going to be saved.
#
# Revision 1.13  2008/01/22 18:42:05  bkline
# Changed sponsorship to allow multiple occurrences; made test output
# conditional.
#
# Revision 1.12  2007/10/18 19:29:50  bkline
# Enhanced exception handling.
#
# Revision 1.11  2006/10/18 20:52:10  bkline
# Modified selection query to avoid importing trials for which we have
# no XML (they're in the table only to force download of the XML in
# the next download job).
#
# Revision 1.10  2006/06/15 13:58:16  bkline
# Removed testing code for new email report.
#
# Revision 1.9  2006/05/18 18:53:49  bkline
# Added email report of failures (request #2094).
#
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
import cdr, cdrdb, sys, xml.sax, re, cdrcgi, xml.dom.minidom

class Flags:
    def __init__(self):
        self.clear()
    def clear(self):
        self.isNew = 'N'
        self.needsReview = 'N'
        self.pubVersionCreated = 'N'
        self.locked = False
        self.terminated = False
        self.isTransferred = False

class CTGovHandler(xml.sax.handler.ContentHandler):
    def __init__(self, flags):
        self.doc      = u""
        self.para     = u""
        self.inPara   = False
        self.flags    = flags
        self.inStatus = False
        self.status   = u""
    def startDocument(self):
        self.doc = u"<?xml version='1.0'?>\n"
    def startElement(self, name, attributes):
        if name == u'Para':
            self.para   = u""
            self.inPara = True
        else:
            if name == 'OverallStatus':
                self.status = u""
                self.inStatus = True
            self.doc += u"<%s" % name
            for attrName in attributes.getNames():
                val = xml.sax.saxutils.quoteattr(attributes.getValue(attrName))
                self.doc += u" %s=%s" % (attrName, val)
            self.doc += u">"
    def endElement(self, name):
        if name == 'Para':
            self.doc += self.parsePara()
            self.inPara = False
            self.para = u""
        else:
            if name == 'OverallStatus':
                if TESTING:
                    print "STATUS: ", self.status
                if self.status.upper().strip() in ("WITHDRAWN", "TERMINATED"):
                    self.flags.terminated = True
                self.inStatus = False
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

def log(msg, cdrErrors = None, tback = False):
    if cdrErrors:
        errors = cdr.getErrors(cdrErrors, asSequence = True)
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
        errors = cdr.getErrors(resp[1], errorsExpected = True,
                               asSequence = False)
        raise Exception(errors)
    if resp[1]:
        errors = cdr.getErrors(resp[1], errorsExpected = False,
                               asSequence = True)
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

def preserveElement(tagName, newXml, dom):
    """
    Extract a specified node from the DOM tree for a CDR document
    and insert the serialized form of that node into the string
    for a CTGovProtocol document, replacing the placeholder inserted
    by the 'Import CT.gov Protocol' filter.

    Pass:
        tagName    - unqualified element name for the node to
                     extract from the DOM for the CDR document;
                     there will be at most one occurrence of
                     the node
        newXml     - string representation of a CTGovProtocol
                     document, containing a placeholder of the
                     form '@@' + tagName + '@@' which will be
                     replaced with the serialized form of the
                     node we're looking for if we find it, or
                     with an empty string if the node is not
                     present; the string is encoded as utf-8
        dom        - object representing the CDR document from
                     which we will extract the node to be
                     preserved

    Return:
        Modified utf-8 string representing the CTGovProtocol
        document with information from a previous version of
        the corresponding CDR document inserted.
    """
    elems = dom.getElementsByTagName(tagName)
    oldXml = elems and elems[0].toxml() or u""
    placeholder = "@@%s@@" % tagName
    return newXml.replace(placeholder, oldXml.encode('utf-8'))

def mergeVersion(newDoc, cdrId, docObject, docVer):
    """
    Merge information added by CIAT in a previous copy of the CDR document
    into the new document we just got from NLM.

    Pass:
        newDoc     - new document received from NLM, after being run
                     through the XSL/T filter 'Import CT.gov Protocol'
        cdrId      - identifier for our own document
        docObject  - object which will be capable of serializing itself
                     into the form ready for passing into the CdrRepDoc
                     command, after we have modified the newDoc string
                     to restore the PDQ information created by CIAT
                     and plugged that modified string into this object
                     as the 'xml' attribute
        docVer     - version of the CDR document from which we will
                     retrieve the PDQ information to preserve

    Return:
        Serialized CdrDoc object, ready to be passed to the CdrRepDoc
        command (encoded as utf-8).
    """
    
    response = cdr.getDoc('guest', cdrId, version = docVer, getObject = True)
    if type(response) in (str, unicode):
        errors = cdr.getErrors(response, errorsExpected = False,
                               asSequence = True)
        raise Exception(errors)
    dom = xml.dom.minidom.parseString(response.xml)
    newDoc = preserveElement('PDQIndexing', newDoc, dom)
    newDoc = preserveElement('PDQProtocolIDs', newDoc, dom)
    newDoc = preserveElement('ProtocolProcessingDetails', newDoc, dom)
    docObject.xml = newDoc
    return str(docObject)

def mergeChanges(cdrId, newDoc, flags):

    response = cdr.getDoc(session, cdrId, checkout = 'Y', getObject = True)
    errors   = cdr.getErrors(response, errorsExpected = False,
                             asSequence = True)
    if errors:
        flags.locked = True
        cursor.execute("""\
        INSERT INTO ctgov_import_event (job, nlm_id, locked, new, transferred)
             VALUES (?, ?, 'Y', 'N', 'N')""", (job, nlmId))
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

    # We only need to save the newCwd once
    # This flag says that we haven't saved it at all yet
    savedNewCwd = False

    # Save the old CWD as a version if appropriate.
    if isChanged == 'Y':
        comment = 'ImportCTGovProtocols: preserving current working doc'
        #print str(docObject)
        response = cdr.repDoc(session, doc = str(docObject), ver = 'Y',
                              reason = comment, comment = comment,
                              showWarnings = True, verPublishable = 'N')
        checkResponse(response)


    # New requirement (#1172): special handling for terminated protocols.
    if flags.terminated:
        if TESTING:
            print "handling terminated doc"
        comment  = 'ImportCTGovProtocols: versioning terminated protocol'
        response = cdr.repDoc(session, doc = newCwd, ver = 'Y',
                              verPublishable = 'N',
                              reason = comment, comment = comment,
                              showWarnings = True, activeStatus = 'I')
        checkResponse(response)
        savedNewCwd = True

    # Has a publishable CTGovProtocol version ever been saved for this trial?
    elif isPublishableCtgovProtocolVersion(cdrId, lastPub):

        # If the differences are not significant, create a new pub. ver.
        if hasMajorDiffs(cdrId, lastPub, newSubset):
            flags.needsReview = 'Y'

        # If the old CWD and the last publishable version are identical
        #   then the newCWD and newPubVer should also be the same
        if not isChanged and lastAny == lastPub:
            newPubVer = newCwd
        else:
            newPubVer = mergeVersion(newDoc, cdrId, docObject, lastPub)
        comment = 'ImportCTGovProtocols: creating new publishable version'
        response = cdr.repDoc(session, doc = newPubVer, ver = 'Y',
                              verPublishable = 'Y', val = 'Y',
                              reason = comment, comment = comment,
                              showWarnings = True)
        errs = checkResponse(response)
        flags.pubVersionCreated = errs and 'N' or 'Y'
        if errs:
            cdr.logwrite("%s: %s" % (cdrId, errs[0]), LOGFILE)

        # If the newCwd and the newPubVer are the same, we've saved both
        if newCwd == newPubVer:
            # They were the same.  Our new CWD was, effectively, saved
            savedNewCwd = True

    elif hasMajorDiffs(cdrId, None, newSubset):
        flags.needsReview = 'Y'

    # Saving a modified publishable version, or a terminated version
    #   also created a new CWD.
    # Otherwise, store a new CWD from the old one updated with NLM's changes.
    if not savedNewCwd:
        comment  = 'ImportCTGovProtocols: creating new CWD'
        response = cdr.repDoc(session, doc = newCwd,
                              reason = comment, comment = comment,
                              showWarnings = True,
                              activeStatus = flags.terminated and 'I' or None)
        checkResponse(response)

#----------------------------------------------------------------------
# Save the CTGovProtocol document for a transferred trial as a new
# version of the InScopeProtocol document for the same trial.
#----------------------------------------------------------------------
def transferTrial(cdrId, newDoc, flags):

    # Check out the InScopeProtocol document
    response = cdr.getDoc(session, cdrId, checkout = 'Y', getObject = True)
    errors = cdr.getErrors(response, errorsExpected = False, asSequence = True)
    if errors:
        flags.locked = True
        cursor.execute("""\
        INSERT INTO ctgov_import_event (job, nlm_id, locked, new, transferred)
             VALUES (?, ?, 'Y', 'N', 'Y')""", (job, nlmId))
        conn.commit()
        raise Exception(errors)
    docObject = response

    # If there are unversioned changes in the CWD, preserve them.
    if cdr.lastVersions(session, cdrId)[2] == 'Y':
        comment = 'ImportCTGovProtocols: preserving current working doc'
        response = cdr.repDoc(session, doc = str(docObject), ver = 'Y',
                              verPublishable = 'N', reason = comment,
                              comment = comment, showWarnings = True,
                              val = 'Y')
        errors = checkResponse(response)
        if errors:
            cdr.logwrite("%s: %s" % (cdrId, errors[0]), LOGFILE)

    # Do the magic to transform the document type and save a new version.
    docObject.type = 'CTGovProtocol'
    docObject.xml = fixTransferredDoc(cdrId, newDoc)
    comment = 'ImportCTGovProtocols: versioning transferred trial'
    response = cdr.repDoc(session, doc = str(docObject), ver = 'Y',
                          verPublishable = 'N', reason = comment, val = 'Y',
                          comment = comment, showWarnings = True,
                          activeStatus = flags.terminated and 'I' or None)
    errors = checkResponse(response)
    if errors:
        cdr.logwrite("%s: %s" % (cdrId, errors[0]), LOGFILE)

#----------------------------------------------------------------------
# Plug in PDQ sponsorship information if appropriate.
#----------------------------------------------------------------------
NIH_INSTITUTE = "NIH INSTITUTE, CENTER, OR DIVISION"
pdqSponsorshipMap = {
    "NATIONAL CANCER INSTITUTE"                                       :"NCI",
    "NATIONAL CENTER FOR COMPLEMENTARY AND ALTERNATIVE MEDICINE"      :"NCCAM",
    "NATIONAL HEART, LUNG, AND BLOOD INSTITUTE"                       :"NHLBI",
    "NATIONAL INSTITUTE OF ALLERGY AND INFECTIOUS DISEASES"           :"NIAID",
    "NATIONAL INSTITUTE OF ARTHRITIS AND MUSCULOSKELETAL DISEASES"    :"NIAMS",
    "NATIONAL INSTITUTE OF ARTHRITIS AND MUSCULOSKELETAL AND SKIN DISEASES"
                                                                      :"NIAMS",
    "NATIONAL INSTITUTE OF DENTAL AND CRANIOFACIAL RESEARCH"          :"NIDCR",
    "NATIONAL INSTITUTE OF DIABETES AND DIGESTIVE AND KIDNEY DISEASES":"NIDDK",
    "NATIONAL INSTITUTE OF NEUROLOGICAL DISORDERS AND STROKE"         :"NINDS",
    "NATIONAL EYE INSTITUTE"                                          :"NEI",
    "NATIONAL INSTITUTE ON AGING"                                     :"NIA",
    "NATIONAL INSTITUTE ON AGING - BETHESDA"                          :"NIA",
    "NATIONAL INSTITUTE OF CHILD HEALTH AND HUMAN DEVELOPMENT"        :"NICHD",
    "NATIONAL INSTITUTE ON DEAFNESS AND OTHER COMMUNICATION DISORDERS":"NIDCD",
    "NATIONAL INSTITUTE OF ENVIRONMENTAL HEALTH SCIENCES"             :"NIEHS",
    "NATIONAL CENTER FOR RESEARCH RESOURCES"                          :"NCRR",
    "NIH - NATIONAL CENTER FOR RESEARCH RESOURCES"                    :"NCRR",
    "NATIONAL HUMAN GENOME RESEARCH INSTITUTE"                        :"NHGRI",
    #"NHGRI - CLINICAL GENETHERAPY BRANCH"                             :"NHGRI",
    "NATIONAL INSTITUTE OF MENTAL HEALTH"                             :"NIMH",
    "NATIONAL INSTITUTE OF GENERAL MEDICAL SCIENCES"                  :"NIGMS",
    "NATIONAL INSTITUTE OF NURSING RESEARCH"                          :"NINR",
    "WARREN GRANT MAGNUSON CLINICAL CENTER"                       :"NIH WGMCC",
    "NIH - WARREN GRANT MAGNUSON CLINICAL CENTER"                 :"NIH WGMCC"
    }
def fixPdqSponsorship(doc):
    pdqSponsorship = set()
    match = spPatt.search(doc)
    if match:
        cdrIds = match.group(1).strip('|').split('|')
        if TESTING and cdrIds:
            print nlmId, "sponsorship IDs:", cdrIds
        for org in cdrIds:
            if org == 'Other':
                pdqSponsorship.add("Other")
                continue
            collaboratorOrSponsorIndicator, cdrId = org.split('=')
            collaborator = collaboratorOrSponsorIndicator == 'C'
            digits = re.sub(r"[^\d]", "", cdrId)
            if digits:
                docId = int(digits)
                cursor.execute("""\
                    SELECT t.name
                      FROM doc_type t
                      JOIN document d
                        ON d.doc_type = t.id
                     WHERE d.id = ?""", docId)
                rows = cursor.fetchall()
                docType = rows and rows[0][0] or None
                if docType == "Person":
                    if not collaborator:
                        pdqSponsorship.add("Other")
                elif docType == 'Organization':
                    cursor.execute("""\
                        SELECT value
                          FROM query_term
                         WHERE path = '/Organization/OrganizationType'
                           AND doc_id = ?""", docId)
                    rows = cursor.fetchall()
                    orgType = rows and rows[0][0].strip().upper() or None
                    if collaborator and orgType != NIH_INSTITUTE:
                        continue
                    if orgType == "PHARMACEUTICAL/BIOMEDICAL":
                        pdqSponsorship.add("Pharmaceutical/Industry")
                    elif orgType == NIH_INSTITUTE:
                        sponsorship = "Other"
                        cursor.execute("""\
                            SELECT value
                              FROM query_term
                             WHERE path = '/Organization'
                                        + '/OrganizationNameInformation'
                                        + '/OfficialName/Name'
                               AND doc_id = ?""", docId)
                        rows = cursor.fetchall()
                        if rows:
                            orgName = rows[0][0].strip().upper()
                            if orgName in pdqSponsorshipMap:
                                sponsorship = pdqSponsorshipMap[orgName]
                        if collaborator:
                            if sponsorship == "NCI":
                                pdqSponsorship.add(sponsorship)
                        else:
                            pdqSponsorship.add(sponsorship)
                    else:
                        pdqSponsorship.add("Other")
                elif not collaborator:
                    pdqSponsorship.add("Other")
            elif not collaborator:
                pdqSponsorship.add("Other")
    sponsorshipVals = list(pdqSponsorship)
    sponsorshipVals.sort()
    if 'Other' in pdqSponsorship:
        sponsorshipVals.remove('Other')
        sponsorshipVals.append('Other')
    if not sponsorshipVals:
        sponsorshipVals = ['Other']
    sponsorshipElems = ["<PDQSponsorship>%s</PDQSponsorship>" % val
                        for val in sponsorshipVals]
    if TESTING and sponsorshipElems:
        print sponsorshipElems
    return spPatt.sub("\n".join(sponsorshipElems), doc)

#----------------------------------------------------------------------
# Assemble a new PDQIndexing block from information in the InScopeProtocol
# document for a trial whose ownership is being transferred from PDQ,
# and insert the block in the CTGovProtocol document which will be saved
# in place as a new version of the InScopeProtocol document for the trial.
# Expanded this function to also pick up PDQ protocol IDs.
#----------------------------------------------------------------------
transferredTrialScript = """\
<?xml version='1.0' encoding='UTF-8'?>
<xsl:transform                version = '1.0' 
                            xmlns:xsl = 'http://www.w3.org/1999/XSL/Transform'
                            xmlns:cdr = 'cips.nci.nih.gov/cdr'>
 <xsl:output                   method = 'xml'/>

 <!--
 =======================================================================
 Top-level template.
 ======================================================================= -->
 <xsl:template                  match = '/'>
  <Wrapper cdr:ref='dummy'>
   <xsl:apply-templates        select = 'InScopeProtocol'/>
  </Wrapper>
 </xsl:template>
 <!--
 =======================================================================
 Document element template.
 ======================================================================= -->
 <xsl:template                  match = 'InScopeProtocol'>
  <PDQIndexing>
   <xsl:apply-templates        select = 'ProtocolDetail/StudyType'/>
   <xsl:apply-templates        select = 'ProtocolDetail/StudyCategory'/>
   <xsl:apply-templates        select = 'ProtocolDesign'/>
   <xsl:apply-templates        select = 'ProtocolDetail/Condition'/>
   <xsl:apply-templates        select = 'ProtocolDetail/Gene'/>
   <xsl:apply-templates        select = 'Eligibility'/>
   <xsl:apply-templates        select = 'ProtocolDetail/EnteredBy'/>
   <xsl:apply-templates        select = 'ProtocolDetail/EntryDate'/>
  </PDQIndexing>
  <PDQProtocolIDs>
   <xsl:apply-templates        select = 'ProtocolIDs/PrimaryID'/>
   <xsl:apply-templates        select = 'ProtocolIDs/OtherID'/>
  </PDQProtocolIDs>
 </xsl:template>

 <!--
 =======================================================================
 Copy most things straight through.
 ======================================================================= -->
 <xsl:template                  match = '@*|node()|comment()|
                                         processing-instruction()'>
  <xsl:copy>
   <xsl:apply-templates        select = '@*|node()|comment()|
                                         processing-instruction()'/>
  </xsl:copy>
 </xsl:template>

 <!--
 =======================================================================
 Cherry-pick from the StudyCategory block.
 ======================================================================= -->
 <xsl:template                  match = 'StudyCategory'>
  <StudyCategory>
   <xsl:apply-templates         select = 'StudyCategoryType'/>
   <xsl:apply-templates         select = 'StudyCategoryName'/>
   <xsl:apply-templates         select = 'Intervention'/>
  </StudyCategory>
 </xsl:template>

 <!--
 =======================================================================
 Cherry-pick from the Intervention block.
 ======================================================================= -->
 <xsl:template                  match = 'Intervention'>
  <Intervention>
   <xsl:apply-templates        select = 'InterventionType'/>
   <xsl:apply-templates        select = 'InterventionNameLink'/>
  </Intervention>
 </xsl:template>

 <!--
 =======================================================================
 Strip these.
 ======================================================================= -->
 <xsl:template                  match = 'Gender|@PdqKey'/>

</xsl:transform>
"""
def fixTransferredDoc(docId, docXml):
    result = cdr.filterDoc('guest', transferredTrialScript, docId,
                           inline = True)
    if type(result) in (str, unicode):
        raise Exception(result)
    dom = xml.dom.minidom.parseString(result[0])
    elements = dom.getElementsByTagName('PDQIndexing')
    if not elements:
        raise Exception("unable to create PDQIndexing block")
    pdqIndexing = elements[0].toxml()
    elements = dom.getElementsByTagName('PDQProtocolIDs')
    if not elements:
        raise Exception("unable to create PDQProtocolIDs block")
    protocolIds = elements[0].toxml()
    docXml = docXml.replace(u"@@PDQIndexing@@", pdqIndexing)
    docXml = docXml.replace(u"@@PDQProtocolIDs@@", protocolIds)
    docXml = docXml.replace(u"@@ProtocolProcessingDetails@@", "")
    return docXml.encode('utf-8')

#----------------------------------------------------------------------
# Determine the current type for a CDR document.
#----------------------------------------------------------------------
def getDocumentType(cdrId):
    cursor.execute("""\
        SELECT t.name
          FROM doc_type t
          JOIN document d
            ON d.doc_type = t.id
         WHERE d.id = ?""", cdrId)
    rows = cursor.fetchall()
    return rows and rows[0][0] or None

#----------------------------------------------------------------------
# Determine whether the specified version is a publishable version of
# a CTGovProtocol document.
#----------------------------------------------------------------------
def isPublishableCtgovProtocolVersion(cdrId, lastPub):
    docId = cdr.exNormalize(cdrId)[1]
    cursor.execute("""\
        SELECT t.name
          FROM doc_type t
          JOIN doc_version v
            ON v.doc_type = t.id
         WHERE v.publishable = 'Y'
           AND v.id = ?
           AND v.num = ?
           AND t.name = 'CTGovProtocol'""", (docId, lastPub))
    return cursor.fetchall() and True or False

#----------------------------------------------------------------------
# Module-scoped data.
#----------------------------------------------------------------------
TESTING = len(sys.argv) > 1 and sys.argv[1].upper().startswith('TEST')
LOGFILE = cdr.DEFAULT_LOGDIR + "/CTGovImport.log"
flags   = Flags()
parser  = CTGovHandler(flags)
spPatt  = re.compile("@@PDQSPONSORSHIP=([^@]*)@@")
conn    = cdrdb.connect()
cursor  = conn.cursor()
session = cdr.login('CTGovImport', '***REMOVED***')
errors  = cdr.getErrors(session, errorsExpected = False, asSequence = True)
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
     WHERE d.name = 'import requested'
       AND c.xml IS NOT NULL""")
rows = cursor.fetchall()
cursor.execute("INSERT into ctgov_import_job (dt) VALUES (GETDATE())")
conn.commit()
cursor.execute("SELECT @@IDENTITY")
job = cursor.fetchone()[0]
failures = []
if TESTING:
    transfersProcessed = 0
    processed = 0
try:
    for nlmId, cdrId in rows:
        flags.clear()
        if TESTING:
            if processed > 10:
                break
            processed += 1
            if transfersProcessed > 0:
                break
            print nlmId, cdrId
        if cdrId:
            docType = getDocumentType(cdrId)
            if TESTING:
                print "%d: %s" % (cdrId, docType)
            if docType == 'InScopeProtocol':
                if TESTING:
                    print "SETTING ISTRANSFERRED FLAG"
                    transfersProcessed += 1
                flags.isTransferred = True
        cursor.execute("SELECT xml FROM ctgov_import WHERE nlm_id = ?", nlmId)
        doc = cursor.fetchone()[0].encode('utf-8')
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
    """ % (comment, doc.encode('utf-8')), showWarnings = True,
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
        # Save newly transferred trial as CTGovProtocol in place as a new
        # version of the corresponding InScopeProtocol document (see issue
        # number 4634).
        #------------------------------------------------------------------
        elif flags.isTransferred:
            try:
                transferTrial(cdrId, doc, flags)
                cursor.execute("""\
                UPDATE ctgov_import
                   SET disposition = ?,
                       dt = GETDATE()
                 WHERE nlm_id = ?""", (importedDisposition, nlmId))
                conn.commit()
                log("Transferred %s as CDR%d" % (nlmId, cdrId))
            except Exception, errors:
                failures.append("Failure transferring %s as CDR%s" %
                                (nlmId, cdrId))
                log("Failure transferring %s as CDR%s: %s\n" %
                    (nlmId, cdrId, errors), tback = (not flags.locked))
            if not flags.locked:
                cdr.unlock(session, "CDR%d" % cdrId,
                           reason = 'ImportCTGovProtocols: '
                                    'Unlocking transferred CTGovProtocol doc')
                
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
                log("Updated CDR%d from %s" % (cdrId, nlmId))
            except Exception, info:
                failures.append("Failure merging changes for %s into %s" %
                                (nlmId, cdrId))
                log("Failure merging changes for %s into %s: %s" %
                    (nlmId, cdrId, str(info)), tback = (not flags.locked))
                #raise
            if not flags.locked:
                cdr.unlock(session, "CDR%d" % cdrId,
                           reason = 'ImportCTGovProtocols: '
                                    'Unlocking updated CTGovProtocol doc')
        if not flags.locked:
            try:
                cursor.execute("""\
     INSERT INTO ctgov_import_event(job, nlm_id, new, needs_review,
                                    pub_version, transferred, locked)
          VALUES (?, ?, ?, ?, ?, ?, 'N')""", (job,
                                              nlmId,
                                              flags.isNew,
                                              flags.needsReview,
                                              flags.pubVersionCreated,
                                              flags.isTransferred
                                              and 'Y' or 'N'))
                conn.commit()
            except Exception, info:
                failures.append("Failure recording import event for %s" %
                                nlmId)
                log("Failure recording import event for %s: %s" %
                    (nlmId, str(info)))
except Exception, e:
    failures.append("Job interrupted: %s" % e)
    log("Job interrupted: %s" % e, tback = True)
if TESTING:
    sys.exit(0)
try:
    if failures:
        recips = getEmailRecipients(cursor, True)
        body = """\
    CT.gov import failures encountered; see logs for more information:

    %s
    """ % "\n".join(failures)
        subject = "CT.gov import failures"
        sender = "cdr@%s" % cdrcgi.WEBSERVER
        cdr.sendMail(sender, recips, subject, body)
except Exception, e:
    log("Failure sending report: %s" % e)
