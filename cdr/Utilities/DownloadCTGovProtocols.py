#----------------------------------------------------------------------
#
# $Id: DownloadCTGovProtocols.py,v 1.5 2004-01-14 19:25:19 bkline Exp $
#
# $Log: not supported by cvs2svn $
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
import socket

LOGFILE = cdr.DEFAULT_LOGDIR + "/CTGovDownload.log"

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
    return cmp(normalizeXml(a), normalizeXml(b))

#----------------------------------------------------------------------
# Object used to track statistics for the download report.
#----------------------------------------------------------------------
class Stats:
    def __init__(self):
        self.newTrials  = 0
        self.updates    = 0
        self.unchanged  = 0
        self.pdqCdr     = 0
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
            SELECT xml, cdr_id, disposition
              FROM ctgov_import
             WHERE nlm_id = ?""", self.nlmId)
                row = cursor.fetchone()
            except Exception, e:
                log("Failure selecting from ctgov_import for %s\n"
                    % self.nlmId)
                sys.exit(1)
            if row:
                self.oldXml, self.cdrId, self.disposition = row

#----------------------------------------------------------------------
# Seed the table with documents we know to be duplicates.
#----------------------------------------------------------------------
conn = cdrdb.connect()
cursor = conn.cursor()
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
    url     = "http://clinicaltrials.gov/search/condition=cancer?studyxml=true"
    urlobj  = urllib.urlopen(url)
    page    = urlobj.read()
    name    = time.strftime("CTGovDownload-%Y%m%d%H%M%S.zip")
    zipFile = open(name, "wb")
    zipFile.write(page)
    zipFile.close()
    log("Trials downloaded to %s\n" % name)
when       = time.strftime("%Y-%m-%d")
file       = zipfile.ZipFile(name)
nameList   = file.namelist()
stats      = Stats()
docsInSet  = {}
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
        docsInSet[doc.nlmId] = 1
    if not doc.nlmId:
        log("Skipping document without NLM ID\n")
    elif not doc.title:
        log("Skipping %s, which has no title\n" % doc.nlmId)
    #elif doc.nciSponsored:
    #    log("Skipping %s, which is NCI sponsored\n" % doc.nlmId)

    #------------------------------------------------------------------
    # Skip documents they got from us in the first place.
    #------------------------------------------------------------------
    elif not doc.cdrId and doc.orgStudyId and doc.orgStudyId.startswith("CDR"):
        log("Skipping %s, which has a CDR ID\n" % doc.nlmId)
        stats.pdqCdr += 1

    #------------------------------------------------------------------
    # We don't want closed or completed trials.
    #------------------------------------------------------------------
    elif not doc.cdrId and (not doc.status or
                            doc.status.upper() not in ("RECRUITING",
                                                       "NOT YET RECRUITING")):
        log("Skipping %s, which has a status of %s\n" % (doc.nlmId,
                                                         doc.status))
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
where   = socket.gethostname()
sender  = "cdr@%s.nci.nih.gov" % where
subject = "CTGov trials downloaded %s on %s" % (when, where)
cursor.execute("""\
    SELECT u.email
      FROM usr u
      JOIN grp_usr gu
        ON gu.usr = u.id
      JOIN grp g
        ON g.id = gu.grp
     WHERE g.name = 'CTGOV Maintainers'
       AND u.email IS NOT NULL
       AND u.email <> ''""")
recips = []
for row in cursor.fetchall():
    recips.append(row[0])
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

""" % (stats.newTrials, stats.updates, stats.unchanged, stats.pdqCdr, 
       stats.duplicates, stats.outOfScope, stats.closed, totals)    
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
    # recips = ['***REMOVED***']
    cdr.sendMail(sender, recips, subject, body)
    log("Mailed download stats to %s\n" % str(recips))
else:
    log("Warning: no email addresses found for report\n")
