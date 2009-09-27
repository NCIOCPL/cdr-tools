#----------------------------------------------------------------------
#
# $Id: DownloadCTGovProtocols.py,v 1.34 2009-09-27 19:30:11 bkline Exp $
#
# $Log: not supported by cvs2svn $
# Revision 1.33  2009/04/24 18:18:16  bkline
# Added a missing value for string interpolation placeholder.
#
# Revision 1.32  2009/03/05 21:35:29  bkline
# Request #4516: handle trials whose ownership has been transferred from
# PDQ to CT.gov.
#
# Revision 1.31  2008/07/21 12:45:16  bkline
# Implementation of revised requirements for request #4132.
#
# Revision 1.30  2008/06/18 16:31:56  bkline
# Added workaround for lame limitations in CT.gov service; suppressed
# new code to block 'alias' documents.
#
# Revision 1.29  2008/06/10 19:48:43  bkline
# Added code to block obsolete CT.gov documents.
#
# Revision 1.28  2008/03/13 20:54:48  bkline
# Normalized CDR ID (stripping out non-digits) in getOncoreNctIds().
#
# Revision 1.27  2008/02/20 18:35:45  bkline
# Added code to collect new NCT IDs for Oncore documents.
#
# Revision 1.26  2008/01/24 15:02:51  bkline
# Fixed handling of utf-8 characters.
#
# Revision 1.25  2008/01/09 22:27:16  bkline
# Changes make to work around breakage caused by unannounced changes to
# NLM's service.  Will restore to using POST when Nick tells us support
# for it has been restore.  Moved "studyxml=true" parameter to the end
# so that if this fails because we exceed a length limitation, the
# failure will not be silent.
#
# Revision 1.24  2007/07/11 20:23:46  bkline
# Modified to detect and report problems with too many NCT IDs.
#
# Revision 1.23  2007/06/21 19:53:51  bkline
# Changed test for detecting documents CT.gov got from us to also include
# trials we used to get from them but have been replaced by our own
# InScopeProtocol documents (see discussion in issue #3324).
#
# Revision 1.22  2007/06/18 20:53:06  bkline
# Added code to remove obsolete NCTIDs (see request #3250).
#
# Revision 1.21  2007/03/22 13:49:01  bkline
# Added code to set new phase column of ctgov_import table.
#
# Revision 1.20  2007/02/02 19:31:42  bkline
# Increased DB timeouts; added code to make sure doc is unlocked
# after inserting NCT ID.
#
# Revision 1.19  2007/02/02 18:30:02  bkline
# Modified to use new signature of ModifyDocs.saveChanges() method.
#
# Revision 1.18  2006/11/14 21:46:18  bkline
# Change made in response to Lakshmi's request that we not skip forced
# import trials, regardless of their status.
#
# Revision 1.17  2006/10/18 20:49:46  bkline
# Added support for forcing download and import of a specific trial.
#
# Revision 1.16  2006/08/22 17:22:55  bkline
# Extra conditions plugged into query.
#
# Revision 1.15  2005/01/24 15:30:52  bkline
# Added code to unlock InScopeProtocol documents; changed zip location.
#
# Revision 1.14  2005/01/19 15:14:52  bkline
# Added code to unlock documents into which we insert NCT IDs.
#
# Revision 1.13  2004/12/20 19:58:50  bkline
# Added tally of NCT IDs inserted into trials.
#
# Revision 1.12  2004/12/10 12:45:49  bkline
# Switched to writing copy of documents into a subdirectory; added
# code to insert NCT IDs into CDR documents we have exported to NLM.
#
# Revision 1.11  2004/08/02 15:55:07  bkline
# Added test to weed out expired users in the CTGov Publishers group.
#
# Revision 1.10  2004/07/28 13:11:27  bkline
# Added code to handle database failure when trying to send out email
# report of failure.
#
# Revision 1.9  2004/07/28 13:07:08  bkline
# Added email report on failure.
#
# Revision 1.8  2004/07/28 12:33:35  bkline
# Added logging for download/zipfile failures.
#
# Revision 1.7  2004/02/24 12:47:17  bkline
# Added code to drop rows from ctgov_import for trials which NLM is no
# longer exporting.
#
# Revision 1.6  2004/01/27 15:04:32  bkline
# Changed email group from CTGOV Maintainers to CTGov Publishers at
# Lakshmi's request.
#
# Revision 1.5  2004/01/14 19:25:19  bkline
# Added support for the new download report requirements.
#
# Revision 1.4  2003/12/18 21:04:41  bkline
# Modified code to check for changes before pulling down a fresh
# copy of the XML for a document markes as "Not yet reviewed,"
# "Needs CIPS feedback," or "Import requested."
#
# Revision 1.3  2003/12/14 19:46:58  bkline
# Added logging to logfile with standard CDR logging facility.
#
# Revision 1.2  2003/12/14 19:07:06  bkline
# Final versions for promotion to production system.
#
# Revision 1.1  2003/11/26 13:01:20  bkline
# Nightly job to pull down the latest set of cancer trials from
# ClinicalTrials.gov.
#
#----------------------------------------------------------------------
import cdr, zipfile, re, xml.dom.minidom, sys, urllib, cdrdb, os, time
import socket, ModifyDocs, glob

LOGFILE   = cdr.DEFAULT_LOGDIR + "/CTGovDownload.log"
developer = '***REMOVED***' # for error reports
server    = socket.gethostname()
session   = cdr.login('CTGovImport', '***REMOVED***')
comment   = "Inserting NCT ID from CTGovProtocol download job."

#----------------------------------------------------------------------
# Log activity, errors to the download log and to the console.
#----------------------------------------------------------------------
def log(what):
    sys.stderr.write(what)
    if what and what[-1] == '\n':
        what = what[:-1]
    cdr.logwrite(what, LOGFILE)

#----------------------------------------------------------------------
# Get the names and codes for the valid CTGov dispositions.
#----------------------------------------------------------------------
def loadDispositions(cursor):
    dispNames = {}
    dispCodes = {}
    cursor.execute("SELECT id, name FROM ctgov_disposition", timeout = 300)
    for row in cursor.fetchall():
        dispNames[row[0]] = row[1]
        dispCodes[row[1]] = row[0]
    return [dispNames, dispCodes]

#----------------------------------------------------------------------
# Collect the CDR and NCT IDs of trials in the Oncore database.
#----------------------------------------------------------------------
def getOncoreNctIds():
    url = "http://%s/u/oncore-id-mappings" % cdr.emailerHost()
    ids = {}
    try:
        urlobj = urllib.urlopen(url)
        page   = urlobj.read()
        dom    = xml.dom.minidom.parseString(page)
        for node in dom.documentElement.childNodes:
            if node.nodeName == 'Trial':
                cdrId = node.getAttribute('PdqID')
                nctId = node.getAttribute('NctID') or u''
                if cdrId:
                    cdrId = re.sub("[^0-9]", "", cdrId)
                    ids[int(cdrId)] = nctId
        log("loaded NCT IDs for %d Oncore trials" % len(ids))
    except Exception, e:
        log("failure loading Oncore NCT IDs: %s" % e)
    return ids

#----------------------------------------------------------------------
# Send the Oncore server any new NCT IDs we got.
#----------------------------------------------------------------------
def postNctIdsToOncore(newIds):
    try:
        payload = [u"""\
<?xml version='1.0' encoding='utf-8' ?>
<NewNCTIds>
"""]
        for cdrId in newIds:
            nctId = newIds[cdrId]
            log("posting NCT ID '%s' to Oncore server for CDR%s" %
                (cdrId, nctId))
            payload.append(u"""\
 <Trial CdrId='%s' NctId='%s'/>
""" % (cdrId, newIds[cdrId]))
        payload.append(u"""\
</NewNCTIds>
""")
        payload = u"".join(payload).encode('utf-8')
        app = "/u/post-oncore-nct-ids"
        import httplib
        conn = httplib.HTTPConnection(cdr.emailerHost())
        conn.request("POST", app, payload)
        response = conn.getresponse()
        if response.status != httplib.OK:
            log("failure posting new Oncore NCT IDs: code=%s reason=%s" %
                (response.status, response.reason))
    except Exception, e:
        log("failure posting new Oncore NCT IDs: %s" % e)

#----------------------------------------------------------------------
# Prepare a CTGovProtocol document for comparison with another version.
#----------------------------------------------------------------------
def normalizeXml(doc):
    response = cdr.filterDoc('guest',
                             ['name:Normalize NLM CTGovProtocol document'],
                             doc = doc)
    if type(response) in (type(""), type(u"")):
        raise Exception(response)
    return response[0]

#----------------------------------------------------------------------
# Compare two versions of a CTGovProtocol doc; return non-zero if 
# different.
#----------------------------------------------------------------------
def compareXml(a, b):
    if a is None or b is None:
        return True
    return cmp(normalizeXml(a), normalizeXml(b))

#----------------------------------------------------------------------
# Gather a list of email recipients for reports.
#----------------------------------------------------------------------
def getEmailRecipients(cursor, includeDeveloper = False):
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
               AND u.email <> ''""", timeout = 300)
        recips = [row[0] for row in cursor.fetchall()]
        if includeDeveloper and developer not in recips:
            recips.append(developer)
        return recips
    except:
        if includeDeveloper:
            return [developer]

#----------------------------------------------------------------------
# Mail a report to the specified recipient list.
#----------------------------------------------------------------------
def sendReport(recips, subject, body):
    sender = "cdr@%s.nci.nih.gov" % server
    cdr.sendMail(sender, recips, subject, body)

#----------------------------------------------------------------------
# Send a failure report; include the developer.
#----------------------------------------------------------------------
def reportFailure(context, message):
    log(message)
    recips = getEmailRecipients(cursor, includeDeveloper = True)
    subject = "CTGov Download Failure Report"
    sendReport(recips, subject, message)
    sys.exit(1)

#----------------------------------------------------------------------
# Object used to track statistics for the download report.
#----------------------------------------------------------------------
class Stats:
    def __init__(self):
        self.newTrials  = 0
        self.updates    = 0
        self.unchanged  = 0
        self.pdqCdr     = 0
        self.nctAdded   = 0
        self.nctRemoved = 0
        self.duplicates = 0
        self.outOfScope = 0
        self.closed     = 0
        self.transfers  = 0
    def totals(self):
        return (self.newTrials + self.updates + self.unchanged + self.pdqCdr +
                self.duplicates + self.outOfScope + self.closed +
                self.transfers)

#----------------------------------------------------------------------
# Objects for a document with too many NCT IDs.
#----------------------------------------------------------------------
idProblems = []
class IdProblem:
    def __init__(self, cdrId, nctIds, nctIdToInsert, nctIdsToRemove):
        self.cdrId = cdrId
        self.nctIds = nctIds
        self.nctIdToInsert = nctIdToInsert
        self.nctIdsToRemove = nctIdsToRemove
        plural = len(nctIds) > 1 and u"s" or ""
        if nctIdToInsert:
            desc = (u"CDR%d: got new ID %s from NLM; doc already has ID%s %s"
                    % (cdrId, nctIdToInsert, plural, u"; ".join(nctIds)))
        else:
            desc = u"CDR%d: too many NCT IDs: %s" % (cdrId, u"; ".join(nctIds))
        if nctIdsToRemove:
            desc += (u"; even after removing %s doc will have multiple IDs"
                     % u" & ".join(nctIdsToRemove))
        self.description = desc.encode('utf-8')
                                 
#----------------------------------------------------------------------
# Check to see if we'll end up with too many NCT Ids; see comment #13
# by Lakshmi in request #3250.
#----------------------------------------------------------------------
def findIdProblem(cdrId, nctIds, nctIdToInsert, nctIdsToRemove):
    idCount = 0
    for nctId in nctIds:
        if nctId not in nctIdsToRemove:
            idCount += 1
    if nctIdToInsert and nctIdToInsert not in nctIdsToRemove:
        idCount += 1
    if idCount > 1:
        return IdProblem(cdrId, nctIds, nctIdToInsert, nctIdsToRemove)
    return None

#----------------------------------------------------------------------
# Find InScopeProtocol which has been transferred to a new owner.
#----------------------------------------------------------------------
def findNewlyTransferredDocs(nlmId):
    cursor.execute("""\
        SELECT a.id
          FROM active_doc a
          JOIN query_term o
            ON o.doc_id = a.id
          JOIN query_term i
            ON i.doc_id = a.id
          JOIN query_term t
            ON t.doc_id = i.doc_id
           AND LEFT(t.node_loc, 8) = LEFT(i.node_loc, 8)
         WHERE o.path = '/InScopeProtocol/CTGovOwnershipTransferInfo'
                      + '/CTGovOwnerOrganization'
           AND i.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDString'
           AND t.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
           AND t.value = 'ClinicalTrials.gov ID'
           AND i.value = ?""", nlmId)
    rows = cursor.fetchall()
    return [row[0] for row in rows]
            
#----------------------------------------------------------------------
# Object representing interesting components of a CTGov trial document.
#----------------------------------------------------------------------
class Doc:
    def __init__(self, xmlFile, name):
        self.name          = name
        self.xmlFile       = unicode(xmlFile, 'utf-8')
        self.dom           = xml.dom.minidom.parseString(xmlFile)
        self.officialTitle = None
        self.briefTitle    = None
        self.nlmId         = None
        self.obsoleteIds   = []
        self.orgStudyId    = None
        self.orgStudyCdrId = None
        self.title         = None
        self.status        = None
        self.nciSponsored  = 0
        self.verified      = None
        self.lastChanged   = None
        self.cdrId         = None
        self.disposition   = None
        self.oldXml        = None
        self.phase         = None
        self.forcedImport  = False
        self.newCtgovOwner = None
        for node in self.dom.documentElement.childNodes:
            if node.nodeName == "id_info":
                for child in node.childNodes:
                    if child.nodeName == "org_study_id":
                        self.orgStudyId = cdr.getTextContent(child).strip()
                        if self.orgStudyId.upper().startswith("CDR"):
                            ids = cdr.exNormalize(self.orgStudyId)
                            self.orgStudyCdrId = ids[1]
                            cursor.execute("""\
    SELECT value
      FROM query_term
     WHERE path = '/InScopeProtocol/CTGovOwnershipTransferInfo'
                + '/CTGovOwnerOrganization'
       AND doc_id = ?""", self.orgStudyCdrId)
                            rows = cursor.fetchall()
                            if rows:
                                self.newCtgovOwner = rows[0][0]
                    elif child.nodeName == "nct_id":
                        self.nlmId = cdr.getTextContent(child).strip()
                    elif child.nodeName == 'nct_alias':
                        obsoleteId = cdr.getTextContent(child).strip()
                        if obsoleteId:
                            self.obsoleteIds.append(obsoleteId)
            elif node.nodeName == "brief_title":
                self.briefTitle = cdr.getTextContent(node).strip()
            elif node.nodeName == "official_title":
                self.officialTitle = cdr.getTextContent(node).strip()
            elif node.nodeName == "sponsors":
                for child in node.getElementsByTagName("agency"):
                    name = cdr.getTextContent(node).strip().upper()
                    if name == "NATIONAL CANCER INSTITUTE (NCI)":
                        self.nciSponsored = 1
                        break
            elif node.nodeName == "overall_status":
                self.status = cdr.getTextContent(node).strip()
            elif node.nodeName == "verification_date":
                self.verified = cdr.getTextContent(node).strip()
            elif node.nodeName == "lastchanged_date":
                self.lastChanged = cdr.getTextContent(node).strip()
            elif node.nodeName == "phase":
                self.phase = cdr.getTextContent(node).strip()
        self.title = self.officialTitle or self.briefTitle
        if self.nlmId:
            row = None
            try:
                cursor.execute("""\
            SELECT xml, cdr_id, disposition, force
              FROM ctgov_import
             WHERE nlm_id = ?""", self.nlmId, timeout = 300)
                row = cursor.fetchone()
            except Exception, e:
                msg = ("Failure selecting from ctgov_import for %s\n"
                       % self.nlmId)
                reportFailure(cursor, msg)
            if row:
                self.oldXml, self.cdrId, self.disposition, forced = row
                if forced == 'Y':
                    self.forcedImport = True

#----------------------------------------------------------------------
# An object of this class is fed to the constructor for each ModifyDocs.Doc
# object, used to insert the NCT ID into existing CDR documents which
# we've exported to NLM, and which are coming back to us with their ID.
#----------------------------------------------------------------------
class NctIdInserter:
    def __init__(self, newId, obsoleteIds):
        assert (newId or obsoleteIds), "NctIdInserter: no NCT IDs to adjust"
        self.newId       = newId
        self.obsoleteIds = obsoleteIds
    def run(self, docObj):
        """
        Modify the XML document passed by inserting an OtherID element
        for the new NCT ID (if present) and/or dropping any obsolete NCT
        IDs identified.
        
        Pre-condition:
            Caller will have determined that at least one of self.newId
            or self.obsoleteIds is present, and that if self.newId is present
            the document does not already have that ID, and that any of
            the obsolete IDs specified are actually present in the document.
        """
        filt = ["""\
<?xml version='1.0' encoding='UTF-8'?>

<xsl:transform                version = '1.0' 
                            xmlns:xsl = 'http://www.w3.org/1999/XSL/Transform'
                            xmlns:cdr = 'cips.nci.nih.gov/cdr'>

 <xsl:output                   method = 'xml'/>

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

"""]

        # Pop in new ID if we have one.
        if self.newId:
            filt.append("""\
 <xsl:template                  match = 'ProtocolIDs'>
  <xsl:copy>
   <xsl:apply-templates        select = '@*|node()|comment()|
                                         processing-instruction()'/>
   <OtherID>
    <IDType>ClinicalTrials.gov ID</IDType>
    <IDString>%s</IDString>
   </OtherID>
  </xsl:copy>
 </xsl:template>

""" % self.newId)

        # Drop any obsolete IDs if there are any.
        if self.obsoleteIds:
            ids = self.obsoleteIds
            idTests = " or ".join([('(IDString = "%s")' % i) for i in ids])
            test = 'not((IDType = "ClinicalTrials.gov ID") and (%s))' % idTests
            filt.append("""\
 <xsl:template                  match = 'OtherID'>
  <xsl:if                        test = '%s'>
   <xsl:copy>
    <xsl:apply-templates       select = '@*|node()|comment()|
                                         processing-instruction()'/>
   </xsl:copy>
  </xsl:if>
 </xsl:template>

 """ % test)

        # Finish the filter document.
        filt.append("""\
</xsl:transform>
""")
        filt = "".join(filt)
        if type(filt) == unicode:
            filt = filt.encode('utf-8')
        f = open('d:/tmp/nctid-filters.txt', 'a')
        f.write(filt)
        f.close()
        result = cdr.filterDoc('guest', filt, doc = docObj.xml, inline = 1)
        if type(result) in (type(""), type(u"")):
            sys.stderr.write("%s: %s\n" % (docObj.id, result))
            return docObj.xml
        return result[0]

#----------------------------------------------------------------------
# Object passed to the saveChanges() method of the Doc object.
# Logging is passed on to the module-wide function used for all
# other logging done for this job.  Used for inserting NCT IDs
# into documents we exported to NLM and which are coming back to
# us with their own ID.
#----------------------------------------------------------------------
class Logger:
    def __log(self, what):
        log(what + '\n')
    log = __log

#----------------------------------------------------------------------
# Determine whether a CDR document already has the NCT ID.
#----------------------------------------------------------------------
def getNctIds(cdrId):
    cursor.execute("""\
        SELECT i.value
          FROM query_term i
          JOIN query_term t
            ON t.doc_id = i.doc_id
           AND LEFT(i.node_loc, 8) = LEFT(t.node_loc, 8)
         WHERE i.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDString'
           AND t.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
           AND t.value = 'ClinicalTrials.gov ID'
           AND i.doc_id = ?""", cdrId, timeout = 300)
    return set([row[0] for row in cursor.fetchall()])

#----------------------------------------------------------------------
# Get the NCT IDs for trials we need to import even if their index
# terms don't fit the criteria for our search query.
#----------------------------------------------------------------------
def getForcedImportIds(cursor):
    conn = cdrdb.connect('CdrGuest', dataSource = 'bach.nci.nih.gov')
    cursor = conn.cursor()
    cursor.execute("SELECT nlm_id FROM ctgov_import WHERE force = 'Y'",
                   timeout = 300)
    return [row[0] for row in cursor.fetchall()]

#----------------------------------------------------------------------
# Request #4132 from Lakshmi:
# If a CTGOV trial has one or more <nct_alias> elements, we need to
# check if we have records in the CDR for any of those nct_alias numbers.
# If we do, we need to block the record(s) and add a comment :
# "Trial blocked because it is a duplicate of NCT xxxxxx"
# where NCT xxxxx is the NCTID of the trial in which the <nct_alias> is
# found.
#----------------------------------------------------------------------
def blockObsoleteCtgovDocs(obsoleteIds, cursor, session, nlmId):

    # [Kim, 2008-06-17] Don't do this if the original isn't in the CDR.
    cursor.execute("""\
        SELECT COUNT(*)
          FROM query_term
         WHERE path = '/CTGovProtocol/IDInfo/NCTID'
           AND value = ?""", nlmId)
    if cursor.fetchall()[0][0] < 1:
        return
    
    comment = (u"Trial blocked because it is a duplicate of %s"
               % nlmId).encode('utf-8')
    for obsoleteId in obsoleteIds:
        # log("looking for obsolete trial '%s'" % obsoleteId)
        cursor.execute("""\
            SELECT DISTINCT q.doc_id
              FROM query_term q
              JOIN active_doc a
                ON a.id = q.doc_id
             WHERE q.path = '/CTGovProtocol/IDInfo/NCTID'
               AND q.value = ?""", obsoleteId, timeout = 300)
        for row in cursor.fetchall():
            
            # [Kim, 2008-06-17] Create a new version and put comment there.
            # cdr.setDocStatus(session, row[0], 'I', comment = comment)
            doc = cdr.getDoc(session, row[0], 'Y')
            err = cdr.checkErr(doc)
            if err:
                log("getDoc(CDR%s): %s" % (row[0], err))
            else:
                response = cdr.repDoc(session, doc = doc, comment = comment,
                                      checkIn = 'Y', reason = comment,
                                      ver = 'Y', activeStatus = 'I',
                                      verPublishable = 'N')
                err = cdr.checkErr(response)
                if err:
                    log("repDoc(CDR%s): %s" % (row[0], err))
                else:
                    log("blocked alias CDR%s (%s)" % (row[0], obsoleteId))

#----------------------------------------------------------------------
# Seed the table with documents we know to be duplicates.
#----------------------------------------------------------------------
tooManyReplacedDocs = []
ModifyDocs._testMode = False
conn = cdrdb.connect()
cursor = conn.cursor()
logger = Logger()
dispNames, dispCodes = loadDispositions(cursor)
oldOncoreNctIds = getOncoreNctIds()
newOncoreNctIds = {}
expr = re.compile(r"CDR0*(\d+)\s+(NCT\d+)\s*")
for line in open('ctgov-dups.txt'):
    match = expr.match(line)
    if match:
        cdrId, nlmId = match.groups()
        cdrId = int(cdrId)
        cursor.execute("""\
            SELECT cdr_id, disposition
              FROM ctgov_import
             WHERE nlm_id = ?""", nlmId, timeout = 300)
        row = cursor.fetchone()
        if row:
            if row[0] != dispCodes['duplicate']:
                if row[0] == dispCodes['imported']:
                    log('duplicate %s already imported as CDR%d\n' %
                        (nlmId, row[1]))
                else:
                    try:
                        cursor.execute("""\
                    UPDATE ctgov_import
                       SET disposition = ?,
                           dt = GETDATE(),
                           cdr_id = ?,
                           comment = 'Marked as duplicate by download job'
                     WHERE nlm_id = ?""", (dispCodes['duplicate'],
                                           cdrId,
                                           nlmId), timeout = 300)
                        conn.commit()
                    except:
                        log('Unable to update row for %s/CDR%d\n' %
                            (nlmId, cdrId))
        else:
            try:
                cursor.execute("""\
            INSERT INTO ctgov_import (nlm_id, cdr_id, disposition, dt,
                                      comment)
                 VALUES (?, ?, ?, GETDATE(),
                         'Marked as duplicate by download job')""",
                           (nlmId, cdrId, dispCodes['duplicate']),
                               timeout = 300)
                conn.commit()
            except:
                log('Unable to insert row for %s/CDR%d\n' %
                    (nlmId, cdrId))

def getForcedDocs(params, counter, cursor):
    params.append('&studyxml=true')
    params = ''.join(params)
    #print params
    name = "force-set-%d.zip" % counter
    #print name
    try:
        #urlobj = urllib.urlopen(url, params)
        urlobj = urllib.urlopen("%s?%s" % (url, params))
        page   = urlobj.read()
    except Exception, e:
        msg = "Failure downloading %s: %s" % (name, str(e))
        reportFailure(cursor, msg)
    try:
        fp = open(name, "wb")
        fp.write(page)
        fp.close()
        log("%s downloaded\n" % name)
    except Exception, e:
        msg = "Failure storing %s: %s" % (name, str(e))
        reportFailure(cursor, msg)
    result = cdr.runCommand("unzip -o %s" % name)
    if result.code:
        msg = "Failure unpacking %s: %s" % (name, result.output)
        reportFailure(cursor, msg)

#----------------------------------------------------------------------
# Decide whether we're really downloading or working from an existing
# archive.
#----------------------------------------------------------------------
if len(sys.argv) > 1:
    name = sys.argv[1]
else:
    now = time.strftime("%Y%m%d%H%M%S")
    curdir = os.getcwd()
    basedir = os.path.join(curdir, "CTGovDownloads")
    workdir = os.path.join(basedir, "work-%s" % now)
    os.makedirs(workdir)
    os.chdir(workdir)
    log("workdir is '%s'\n" % workdir)
    conditions = ('cancer', 'lymphedema', 'myelodysplastic syndromes',
                  'neutropenia', 'aspergillosis', 'mucositis')
    connector = ''
    params = ["term="]
    url  = "http://clinicaltrials.gov/ct/search"
    url  = "http://clinicaltrials.gov/ct2/results"
    for condition in conditions:
        params.append(connector)
        params.append('(')
        params.append(condition.replace(' ', '+'))
        params.append(')+%5BCONDITION%5D')
        connector = '+OR+'
    params.append('&studyxml=true')
    params = ''.join(params)
    #print params
    try:
        # POST is broken again: NLM ignores the 'studyxml' paramater
        # when they get a POST request.
        # urlobj = urllib.urlopen(url, params) # POST request
        urlobj = urllib.urlopen("%s?%s" % (url, params)) # GET request
        page   = urlobj.read()
    except Exception, e:
        msg = "Failure downloading core set: %s" % str(e)
        reportFailure(cursor, msg)
    try:
        fp = open("core-set.zip", "wb")
        fp.write(page)
        fp.close()
        log("core set downloaded\n")
    except Exception, e:
        msg = "Failure storing downloaded trials: %s" % str(e)
        reportFailure(cursor, msg)
    result = cdr.runCommand("unzip -o core-set.zip")
    if result.code:
        msg = "Failure unpacking core set: %s" % result.output
        reportFailure(cursor, msg)
    downloaded = set([n[:-4].upper() for n in glob.glob("*.xml")])
    connector = ''
    params = ["term="]
    forcedIds = getForcedImportIds(cursor)
    counter = 1
    for nctId in forcedIds:
        if nctId.upper() not in downloaded:
            params.append(connector)
            params.append(nctId)
            downloaded.add(nctId.upper())
            connector = '+OR+'

            # Don't ask for more than 10 forced documents at a time
            # (NLM has imposed arbitrary limits on our queries because
            # they're unwilling to do the work to determine that
            # we're not a hacker).
            if (len(params) / 2) > 10:
                getForcedDocs(params, counter, cursor)
                counter += 1
                connector = ''
                params = ["term="]

    # Take care of any leftover 'force' documents.
    if len(params) > 1:
        getForcedDocs(params, counter, cursor)
    name = "CTGovDownload-%s.zip" % now
    result = cdr.runCommand("zip ../%s *.xml" % name)
    if result.code:
        msg = "Failure repacking trials: %s" % result.output
        reportFailure(cursor, msg)
    os.chdir(curdir)
    name = "CTGovDownloads/%s" % name
    log("full set in '%s'\n" % name)
    #print name
    #sys.exit(0)
when = time.strftime("%Y-%m-%d")
try:
    file     = zipfile.ZipFile(name)
    nameList = file.namelist()
except Exception, e:
    msg = "Failure opening %s: %s" % (name, str(e))
    reportFailure(cursor, msg)
stats      = Stats()
docsInSet  = set()
logDropped = 1
if len(sys.argv) > 2:
    logDropped = 0

#----------------------------------------------------------------------
# Walk through the archive and process each document in it.
#----------------------------------------------------------------------
for name in nameList:
    wanted = 0
    xmlFile = file.read(name)
    doc = Doc(xmlFile, name)
    if doc.newCtgovOwner:
        log(u"New CT.gov owner for %s is %s\n" % (doc.nlmId, doc.newCtgovOwner))

    #------------------------------------------------------------------
    # Added for enhancement request #4132.
    # Turned off while the requirements get settled.
    #------------------------------------------------------------------
    if doc.obsoleteIds and doc.nlmId:
        blockObsoleteCtgovDocs(doc.obsoleteIds, cursor, session, doc.nlmId)

    #------------------------------------------------------------------
    # Handle some really unexpected problems.
    #------------------------------------------------------------------
    if logDropped and doc.nlmId:
        docsInSet.add(doc.nlmId)
    if not doc.nlmId:
        log("Skipping document without NLM ID\n")
    elif not doc.title:
        log("Skipping %s, which has no title\n" % doc.nlmId)
    #elif doc.nciSponsored:
    #    log("Skipping %s, which is NCI sponsored\n" % doc.nlmId)

    #------------------------------------------------------------------
    # Skip documents they got from us in the first place.
    # Request #1374: pick up the NCT IDs for these documents.
    # Request #4516: handle trials whose ownership has been transferred
    #                from PDQ to CT.gov
    #------------------------------------------------------------------
    elif doc.orgStudyCdrId and doc.newCtgovOwner is None:
        cdrId = doc.orgStudyCdrId
        if cdrId in oldOncoreNctIds and oldOncoreNctIds[cdrId] != doc.nlmId:
            newOncoreNctIds[cdrId] = doc.nlmId
        log("Skipping %s, which has a CDR ID\n" % doc.nlmId)
        stats.pdqCdr += 1
        try:
            locked = False
            nctIds = getNctIds(cdrId)

            # See if we need to insert the current NCT ID.
            nctIdToInsert = None
            if doc.nlmId not in nctIds:
                log("Inserting NCT ID %s into CDR%s\n" % (doc.nlmId, cdrId))
                nctIdToInsert = doc.nlmId
                stats.nctAdded += 1

            # Request #3250: remove obsolete NCT IDs.
            nctIdsToRemove = []
            for obsoleteId in doc.obsoleteIds:
                if obsoleteId in nctIds:
                    log("Removing NCT ID %s from CDR%s\n" % (obsoleteId,
                                                             cdrId))
                    nctIdsToRemove.append(obsoleteId)
                    stats.nctRemoved += 1

            # See comment #13 of request #3250.
            idProblem = findIdProblem(cdrId, nctIds, nctIdToInsert,
                                      nctIdsToRemove)
            if idProblem:
                log(idProblem.description)
                idProblems.append(idProblem)
            elif nctIdToInsert or nctIdsToRemove:
                inserter = NctIdInserter(nctIdToInsert, nctIdsToRemove)
                locked = True
                cdrDoc = ModifyDocs.Doc(cdrId, session, inserter, comment)
                cdrDoc.saveChanges(cursor, logger)
                cdr.unlock(session, "CDR%010d" % cdrId)
                locked = False
        except Exception, e:
            if locked:
                cdr.unlock(session, "CDR%010d" % cdrId)
            log("Failure adjusting NCT IDs in CDR%s: %s" % (cdrId, str(e)))

    #------------------------------------------------------------------
    # We don't want closed or completed trials.
    #------------------------------------------------------------------
    elif (not doc.cdrId and
          not doc.forcedImport and
          doc.newCtgovOwner is None and
          (not doc.status or doc.status.upper() not in ("NOT YET RECRUITING",
                                                        "RECRUITING"))):
        log("Skipping %s, which has a status of %s\n" % (doc.nlmId,
                                                         doc.status))

        # 2004-02-12, request (#1106) from Lakshmi: drop the row if it exists.
        if doc.disposition is not None:
            try:
                cursor.execute("DELETE ctgov_import WHERE nlm_id = ?",
                               doc.nlmId, timeout = 300)
                conn.commit()
                log("dropped existing row for %s\n" % doc.nlmId)
            except Exception, e:
                log("failure dropping row for %s: %s\n" % (doc.nlmId, str(e)))

        stats.closed += 1

    #------------------------------------------------------------------
    # Handle the documents we've already got.
    #------------------------------------------------------------------
    elif doc.disposition:
        disp = doc.disposition
        dispName = dispNames[disp]
        if dispName in ('out of scope', 'duplicate'):
            log("Skipping %s, disposition is %s\n" % (doc.nlmId, dispName))
            if dispName == 'out of scope':
                stats.outOfScope += 1
            else:
                stats.duplicates += 1
            continue
        elif not compareXml(doc.oldXml, doc.xmlFile):
            log("Skipping %s (already imported, unchanged at NLM)\n" 
                % doc.nlmId)
            stats.unchanged += 1
            continue
        if dispName == 'imported':
            disp = dispCodes['import requested']
        try:
            cursor.execute("""\
                UPDATE ctgov_import
                   SET title = ?,
                       xml = ?,
                       downloaded = GETDATE(),
                       disposition = ?,
                       dt = GETDATE(),
                       verified = ?,
                       changed = ?,
                       phase = ?
                 WHERE nlm_id = ?""",
                           (doc.title[:255],
                            doc.xmlFile,
                            disp,
                            doc.verified,
                            doc.lastChanged,
                            doc.phase,
                            doc.nlmId), timeout = 300)
            conn.commit()
            stats.updates += 1
            log("Updated %s with disposition %s\n" % (doc.nlmId,
                                                      dispNames[disp]))
        except Exception, info:
            log("Failure updating %s: %s\n" % (doc.nlmId, str(info)))

    #------------------------------------------------------------------
    # Process new trials.
    #------------------------------------------------------------------
    else:
        replacedDocs = findNewlyTransferredDocs(doc.nlmId)
        if len(replacedDocs) > 1:
            msg = ("Skipping %s: too many replaced docs (%s)" % (doc.nlmId,
                                                                 replacedDocs))
            tooManyReplacedDocs.append(msg)
            log(msg)
            continue
        replacedDoc = replacedDocs and replacedDocs[0] or None
        if doc.forcedImport or replacedDoc: #doc.newCtgovOwner:
            disp = dispCodes['import requested']
        else:
            disp = dispCodes['not yet reviewed']
        try:
            cursor.execute("""\
        INSERT INTO ctgov_import (nlm_id, title, xml, downloaded, cdr_id,
                                  disposition, dt, verified, changed, phase)
             VALUES (?, ?, ?, GETDATE(), ?, ?, GETDATE(), ?, ?, ?)""",
                           (doc.nlmId,
                            doc.title[:255],
                            doc.xmlFile,
                            replacedDoc,
                            disp,
                            doc.verified,
                            doc.lastChanged,
                            doc.phase), timeout = 300)
            conn.commit()
            if replacedDoc:
                stats.transfers += 1
                log("Transferred %s as CDR%d\n" % (doc.nlmId, replacedDoc))
            else:
                stats.newTrials += 1
                log("Added %s with disposition %s\n" % (doc.nlmId,
                                                        dispNames[disp]))
        except Exception, info:
            log("Failure importing %s: %s\n" % (doc.nlmId, str(info)))

#----------------------------------------------------------------------
# Send the Oncore server any new NCT IDs we've collected.
#----------------------------------------------------------------------
if newOncoreNctIds:
    postNctIdsToOncore(newOncoreNctIds)

#----------------------------------------------------------------------
# Find out which trials are no longer being sent by NLM.
#----------------------------------------------------------------------
droppedDocs = {}
if logDropped:
    class DroppedDoc:
        def __init__(self, nlmId, cdrId, disposition):
            self.nlmId       = nlmId
            self.cdrId       = cdrId
            self.disposition = disposition
    cursor.execute("""\
        SELECT nlm_id, disposition, cdr_id, dropped
          FROM ctgov_import""", timeout = 300)
    rows = cursor.fetchall()
    for row in rows:
        dispName = dispNames[row[1]]
        dropped = 'N'
        if row[0] not in docsInSet and dispName != 'duplicate':
            dropped = 'Y'
            droppedDocs[row[0]] = DroppedDoc(row[0], row[2], dispName)
        if dropped != row[3]:
            try:
                cursor.execute("""\
                    UPDATE ctgov_import
                       SET dropped = ?
                     WHERE nlm_id = ?""", (dropped, row[0]), timeout = 300)
                conn.commit()
            except Exception, e:
                log("Failure setting dropped flag to '%s' for %s: %s\n",
                    (dropped, row[0], str(e)))

#----------------------------------------------------------------------
# Log the download statistics.
#----------------------------------------------------------------------
totals = stats.totals()
log("                 New trials: %5d\n" % stats.newTrials)
log("         Transferred trials: %5d\n" % stats.transfers)
log("             Updated trials: %5d\n" % stats.updates)
log("   Skipped unchanged trials: %5d\n" % stats.unchanged)
log("Skipped trials from PDQ/CDR: %5d\n" % stats.pdqCdr)
log("   Skipped duplicate trials: %5d\n" % stats.duplicates)
log("Skipped out of scope trials: %5d\n" % stats.outOfScope)
log("      Skipped closed trials: %5d\n" % stats.closed)
log("               Total trials: %5d\n" % totals)
log("   Added NCT IDs for trials: %5d\n" % stats.nctAdded)
log("Removed NCT IDs from trials: %5d\n" % stats.nctRemoved)
log("   NCT ID problems detected: %5d\n" % len(idProblems))
try:
    cursor.execute("""\
        INSERT INTO ctgov_download_stats (dt, total_trials, new_trials,
                                          transferred,
                                          updated, unchanged, pdq_cdr,
                                          duplicates, out_of_scope, closed)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                   (when, totals, stats.newTrials, stats.transfers,
                    stats.updates,
                    stats.unchanged, stats.pdqCdr, stats.duplicates, 
                    stats.outOfScope, stats.closed), timeout = 300)
    conn.commit()
except Exception, e:
    log("Failure logging download statistics: %s\n" % str(e))

#----------------------------------------------------------------------
# Send out an immediate email report.
#----------------------------------------------------------------------
subject = "CTGov trials downloaded %s on %s" % (when, server)
recips  = getEmailRecipients(cursor)
recips = ['***REMOVED***']
if recips:
    body = """\
                            New trials: %5d
                    Transferred trials: %5d
                        Updated trials: %5d
              Skipped unchanged trials: %5d
           Skipped trials from PDQ/CDR: %5d
              Skipped duplicate trials: %5d
           Skipped out of scope trials: %5d
   Skipped closed and completed trials: %5d
                          Total trials: %5d
              Added NCT IDs for trials: %5d
           Removed NCT IDs from trials: %5d
              NCT ID problems detected: %5d
     CT.gov transfer problems detected: %5d

""" % (stats.newTrials, stats.transfers, stats.updates,
       stats.unchanged, stats.pdqCdr, 
       stats.duplicates, stats.outOfScope, stats.closed, totals,
       stats.nctAdded, stats.nctRemoved, len(idProblems),
       len(tooManyReplacedDocs))
    if droppedDocs:
        keys = droppedDocs.keys()
        keys.sort()
        for key in keys:
            droppedDoc = droppedDocs[key]
            if droppedDoc.cdrId:
                body += """\
Trial %s [disposition '%s'] (imported as CDR%d) dropped by NLM.
""" % (droppedDoc.nlmId, droppedDoc.disposition, droppedDoc.cdrId)
            else:
                body += """\
Trial %s [disposition %s] dropped by NLM.
""" % (droppedDoc.nlmId, droppedDoc.disposition)
    for idProblem in idProblems:
        body += idProblem.description + "\n"
    for tooMany in tooManyReplacedDocs:
        body += tooMany + "\n"
    sendReport(recips, subject, body)
    log("Mailed download stats to %s\n" % str(recips))
else:
    log("Warning: no email addresses found for report\n")
cdr.logout(session)
