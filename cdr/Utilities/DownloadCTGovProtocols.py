#----------------------------------------------------------------------
#
# $Id: DownloadCTGovProtocols.py,v 1.19 2007-02-02 18:30:02 bkline Exp $
#
# $Log: not supported by cvs2svn $
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
import socket, ModifyDocs

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
    cursor.execute("SELECT id, name FROM ctgov_disposition")
    for row in cursor.fetchall():
        dispNames[row[0]] = row[1]
        dispCodes[row[1]] = row[0]
    return [dispNames, dispCodes]

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
               AND u.email <> ''""")
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
        self.duplicates = 0
        self.outOfScope = 0
        self.closed     = 0
    def totals(self):
        return (self.newTrials + self.updates + self.unchanged + self.pdqCdr +
                self.duplicates + self.outOfScope + self.closed)

#----------------------------------------------------------------------
# Object representing interesting components of a CTGov trial document.
#----------------------------------------------------------------------
class Doc:
    def __init__(self, xmlFile, name):
        self.name          = name
        self.xmlFile       = xmlFile
        self.dom           = xml.dom.minidom.parseString(xmlFile)
        self.officialTitle = None
        self.briefTitle    = None
        self.nlmId         = None
        self.orgStudyId    = None
        self.title         = None
        self.status        = None
        self.nciSponsored  = 0
        self.verified      = None
        self.lastChanged   = None
        self.cdrId         = None
        self.disposition   = None
        self.oldXml        = None
        self.forcedImport  = False
        for node in self.dom.documentElement.childNodes:
            if node.nodeName == "id_info":
                for child in node.childNodes:
                    if child.nodeName == "org_study_id":
                        self.orgStudyId = cdr.getTextContent(child).strip()
                    elif child.nodeName == "nct_id":
                        self.nlmId = cdr.getTextContent(child).strip()
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
        self.title = self.officialTitle or self.briefTitle
        if self.nlmId:
            row = None
            try:
                cursor.execute("""\
            SELECT xml, cdr_id, disposition, force
              FROM ctgov_import
             WHERE nlm_id = ?""", self.nlmId)
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
# An object of this class if fed to the constructor for each ModifyDocs.Doc
# object, used to insert the NCT ID into existing CDR documents which
# we've exported to NLM, and which are coming back to us with their ID.
#----------------------------------------------------------------------
class NctIdInserter:
    def __init__(self, nctId):
        self.nctId = nctId
    def run(self, docObj):
        filt = """\
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

 <!-- Add NCT ID if not already present. -->
 <xsl:template                  match = 'ProtocolIDs'>
  <xsl:copy>
   <xsl:apply-templates        select = '@*|node()|comment()|
                                         processing-instruction()'/>
   <xsl:if                       test = 'not(OtherID
                                         [IDType = "ClinicalTrials.gov ID"])'>
    <OtherID>
     <IDType>ClinicalTrials.gov ID</IDType>
     <IDString>%s</IDString>
    </OtherID>
   </xsl:if>
  </xsl:copy>
 </xsl:template>
</xsl:transform>
""" % self.nctId
        if type(filt) == type(u""):
            filt = filt.encode('utf-8')
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
def alreadyHasNctId(cdrId):
    cursor.execute("""\
        SELECT i.value
          FROM query_term i
          JOIN query_term t
            ON t.doc_id = i.doc_id
           AND LEFT(i.node_loc, 8) = LEFT(t.node_loc, 8)
         WHERE i.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDString'
           AND t.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
           AND t.value = 'ClinicalTrials.gov ID'
           AND i.doc_id = ?""", cdrId)
    rows = cursor.fetchall()
    return rows and rows[0][0] and True or False

#----------------------------------------------------------------------
# Get the NCT IDs for trials we need to import even if their index
# terms don't fit the criteria for our search query.
#----------------------------------------------------------------------
def getForcedImportIds(cursor):
    cursor.execute("SELECT nlm_id FROM ctgov_import WHERE force = 'Y'")
    return [row[0] for row in cursor.fetchall()]

#----------------------------------------------------------------------
# Seed the table with documents we know to be duplicates.
#----------------------------------------------------------------------
ModifyDocs._testMode = False
conn = cdrdb.connect()
cursor = conn.cursor()
logger = Logger()
dispNames, dispCodes = loadDispositions(cursor)
expr = re.compile(r"CDR0*(\d+)\s+(NCT\d+)\s*")
for line in open('ctgov-dups.txt'):
    match = expr.match(line)
    if match:
        cdrId, nlmId = match.groups()
        cdrId = int(cdrId)
        cursor.execute("""\
            SELECT cdr_id, disposition
              FROM ctgov_import
             WHERE nlm_id = ?""", nlmId)
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
                                           nlmId))
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
                           (nlmId, cdrId, dispCodes['duplicate']))
                conn.commit()
            except:
                log('Unable to insert row for %s/CDR%d\n' %
                    (nlmId, cdrId))

#----------------------------------------------------------------------
# Decide whether we're really downloading or working from an existing
# archive.
#----------------------------------------------------------------------
if len(sys.argv) > 1:
    name = sys.argv[1]
else:
    conditions = ('cancer', 'lymphedema', 'myelodysplastic syndromes',
                  'neutropenia', 'aspergillosis', 'mucositis')
    connector = ''
    url  = "http://clinicaltrials.gov/ct/search"
    params = ["studyxml=true&term="]
    for condition in conditions:
        params.append(connector)
        params.append('(')
        params.append(condition.replace(' ', '+'))
        params.append(')+%5BCONDITION%5D')
        connector = '+OR+'
    for nctId in getForcedImportIds(cursor):
        params.append(connector)
        params.append(nctId)
    params = ''.join(params)
    #print url
    #print params
    #sys.exit(0)
    try:
        urlobj = urllib.urlopen(url, params)
        page   = urlobj.read()
    except Exception, e:
        msg = "Failure downloading trials: %s" % str(e)
        reportFailure(cursor, msg)
    name = time.strftime("CTGovDownloads/CTGovDownload-%Y%m%d%H%M%S.zip")
    try:
        zipFile = open(name, "wb")
        zipFile.write(page)
        zipFile.close()
        log("Trials downloaded to %s\n" % name)
        # sys.exit(0)
    except Exception, e:
        msg = "Failure storing downloaded trials: %s" % str(e)
        reportFailure(cursor, msg)
when       = time.strftime("%Y-%m-%d")
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
    #------------------------------------------------------------------
    elif not doc.cdrId and doc.orgStudyId and doc.orgStudyId.startswith("CDR"):
        cdrId = cdr.exNormalize(doc.orgStudyId)[1]
        log("Skipping %s, which has a CDR ID\n" % doc.nlmId)
        stats.pdqCdr += 1
        try:
            if not alreadyHasNctId(cdrId):
                log("Adding NCT ID %s to CDR%s" % (doc.nlmId, cdrId))
                inserter = NctIdInserter(doc.nlmId)
                cdrDoc = ModifyDocs.Doc(cdrId, session, inserter, comment)
                cdrDoc.saveChanges(cursor, logger)
                cdr.unlock(session, "CDR%010d" % cdrId)
                stats.nctAdded += 1
        except Exception, e:
            log("Failure adding NCT ID %s to CDR%s: %s" % (doc.nlmId,
                                                           cdrId, str(e)))

    #------------------------------------------------------------------
    # We don't want closed or completed trials.
    #------------------------------------------------------------------
    elif (not doc.cdrId and
          not doc.forcedImport and
          (not doc.status or doc.status.upper() not in ("NOT YET RECRUITING",
                                                        "RECRUITING"))):
        log("Skipping %s, which has a status of %s\n" % (doc.nlmId,
                                                         doc.status))

        # 2004-02-12, request (#1106) from Lakshmi: drop the row if it exists.
        if doc.disposition is not None:
            try:
                cursor.execute("DELETE ctgov_import WHERE nlm_id = ?",
                               doc.nlmId)
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
                       changed = ?
                 WHERE nlm_id = ?""",
                           (doc.title[:255],
                            doc.xmlFile,
                            disp,
                            doc.verified,
                            doc.lastChanged,
                            doc.nlmId))
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
        if doc.forcedImport:
            disp = dispCodes['import requested']
        else:
            disp = dispCodes['not yet reviewed']
        try:
            cursor.execute("""\
        INSERT INTO ctgov_import (nlm_id, title, xml, downloaded,
                                  disposition, dt, verified, changed)
             VALUES (?, ?, ?, GETDATE(), ?, GETDATE(), ?, ?)""",
                           (doc.nlmId,
                            doc.title[:255],
                            doc.xmlFile,
                            disp,
                            doc.verified,
                            doc.lastChanged))
            conn.commit()
            stats.newTrials += 1
            log("Added %s with disposition %s\n" % (doc.nlmId,
                                                    dispNames[disp]))
        except Exception, info:
            log("Failure importing %s: %s\n" % (doc.nlmId, str(info)))

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
          FROM ctgov_import""")
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
                     WHERE nlm_id = ?""", (dropped, row[0]))
                conn.commit()
            except Exception, e:
                log("Failure setting dropped flag to '%s' for %s: %s\n",
                    (dropped, row[0], str(e)))

#----------------------------------------------------------------------
# Log the download statistics.
#----------------------------------------------------------------------
totals = stats.totals()
log("                 New trials: %5d\n" % stats.newTrials)
log("             Updated trials: %5d\n" % stats.updates)
log("   Skipped unchanged trials: %5d\n" % stats.unchanged)
log("Skipped trials from PDQ/CDR: %5d\n" % stats.pdqCdr)
log("   Skipped duplicate trials: %5d\n" % stats.duplicates)
log("Skipped out of scope trials: %5d\n" % stats.outOfScope)
log("      Skipped closed trials: %5d\n" % stats.closed)
log("               Total trials: %5d\n" % totals)
log("   Added NCT IDs for trials: %5d\n" % stats.nctAdded)
try:
    cursor.execute("""\
        INSERT INTO ctgov_download_stats (dt, total_trials, new_trials,
                                          updated, unchanged, pdq_cdr,
                                          duplicates, out_of_scope, closed)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                   (when, totals, stats.newTrials, stats.updates,
                    stats.unchanged, stats.pdqCdr, stats.duplicates, 
                    stats.outOfScope, stats.closed))
    conn.commit()
except Exception, e:
    log("Failure logging download statistics: %s\n" % str(e))

#----------------------------------------------------------------------
# Send out an immediate email report.
#----------------------------------------------------------------------
subject = "CTGov trials downloaded %s on %s" % (when, server)
recips  = getEmailRecipients(cursor)
if recips:
    body = """\
                            New trials: %5d
                        Updated trials: %5d
              Skipped unchanged trials: %5d
           Skipped trials from PDQ/CDR: %5d
              Skipped duplicate trials: %5d
           Skipped out of scope trials: %5d
   Skipped closed and completed trials: %5d
                          Total trials: %5d
              Added NCT IDs for trials: %5d

""" % (stats.newTrials, stats.updates, stats.unchanged, stats.pdqCdr, 
       stats.duplicates, stats.outOfScope, stats.closed, totals,
       stats.nctAdded)    
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
    sendReport(recips, subject, body)
    log("Mailed download stats to %s\n" % str(recips))
else:
    log("Warning: no email addresses found for report\n")
cdr.logout(session)
