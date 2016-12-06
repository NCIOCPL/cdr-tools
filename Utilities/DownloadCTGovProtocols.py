#----------------------------------------------------------------------
#
# $Id$
#
# BZIssue::3250
# BZIssue::3324
# BZIssue::4132
# BZIssue::4516
# BZIssue::4747
# BZIssue::4817
# BZIssue::5294 (OCECDR-3595)
# JIRA::OCECTS-113
# OCECDR-4120: GovDelivery Report for ClinicalTrials
#
#----------------------------------------------------------------------
import cdr
import cdrdb
import cStringIO
import datetime
import lxml.etree as etree
import os
import re
import socket
import sys
import requests
import zipfile

BASE      = "https://trials.nci.nih.gov/pa/pdqgetFileByDate.action"
TIMEOUT   = 60 * 25
LOGFILE   = cdr.DEFAULT_LOGDIR + "/CTGovDownload.log"
FILENAME  = "CTRP-TO-CANCER-GOV-EXPORT-%s.zip"
DIR       = cdr.WORK_DRIVE + ":\\cdr\\Output\\CTRP_Trial_Sets"
developer = "***REMOVED***" # for error reports
server    = socket.gethostname()
session   = cdr.login("CTGovImport", "***REMOVED***")
comment   = "Inserting NCT ID from CTGovProtocol download job."

#----------------------------------------------------------------------
# Log activity, errors to the download log and to the console.
#----------------------------------------------------------------------
def log(what, traceback = False):
    sys.stderr.write(what)
    if what and what[-1] == "\n":
        what = what[:-1]
    cdr.logwrite(what, LOGFILE, tback = traceback)

#----------------------------------------------------------------------
# Get the names and codes for the valid CTGov dispositions.
#----------------------------------------------------------------------
class Dispositions:
    def __init__(self, cursor):
        self.names = {}
        self.codes = {}
        cursor.execute("SELECT id, name FROM ctgov_disposition",
                       timeout=TIMEOUT)
        for code, name in cursor.fetchall():
            self.names[code] = name
            self.codes[name]= code

#----------------------------------------------------------------------
# Object which can strip out the ephemeral parts of a trial document.
#----------------------------------------------------------------------
class Normalizer:
    filter_name = "Normalize NLM CTGovProtocol document"
    def __init__(self, cursor):
        query = cdrdb.Query("document d", "d.xml")
        query.join("doc_type t", "t.id = d.doc_type")
        query.where("t.name = 'Filter'")
        query.where("d.title = '%s'" % self.filter_name)
        rows = query.execute(cursor).fetchall()
        if not rows:
            raise Exception("%s not found" % repr(self.filter_name))
        root = etree.XML(rows[0][0].encode("utf-8"))
        self.transform = etree.XSLT(root)
    def normalize(self, doc):
        if isinstance(doc, unicode):
            doc = doc.encode("utf-8")
        fp = cStringIO.StringIO(doc)
        tree = etree.parse(fp)
        return etree.tostring(self.transform(tree))

#----------------------------------------------------------------------
# Compare two versions of a CTGovProtocol doc; return non-zero if
# different.
#----------------------------------------------------------------------
def compareXml(a, b):
    if a is None or b is None:
        return True
    return cmp(normalizer.normalize(a), normalizer.normalize(b))

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
               AND u.email <> ''""", timeout=TIMEOUT)
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
def reportFailure(message, include_traceback=True):
    log(message, include_traceback)
    recips = getEmailRecipients(cursor, includeDeveloper=True)
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
        self.closed     = 0
    def totals(self):
        return (self.newTrials + self.updates + self.unchanged + self.closed)

#----------------------------------------------------------------------
# Get text content for a document node, stripping leading and trailing
# whitespace.
#----------------------------------------------------------------------
def getStrippedTextContent(node):
    try:
        return node.text.strip()
    except:
        return u""

#----------------------------------------------------------------------
# Object representing interesting components of a CTGov trial document.
#----------------------------------------------------------------------
class Doc:

    #------------------------------------------------------------------
    # Include trials with these statuses in what we import and publish.
    #------------------------------------------------------------------
    wantedStatuses = set(["recruiting", "available", "not yet recruiting",
                          "enrolling by invitation", "suspended",
                          "temporarily not available"])
    activeStatuses = set(["recruiting", "available", 
                          "enrolling by invitation"])
    "For OCECDR-4120 report; adjust list to match requirements."

    def __init__(self, xmlFile, name):
        self.name           = name
        self.xmlFile        = unicode(xmlFile, "utf-8")
        self.root           = etree.XML(xmlFile)
        self.nlmId          = None
        self.title          = None
        self.status         = None
        self.verified       = None
        self.lastChanged    = None
        self.cdrId          = None
        self.disposition    = None
        self.oldXml         = None
        self.phase          = None
        self.activeStatus   = None
        self.becameActive   = None
        briefTitle = officialTitle = None
        for node in self.root:
            if node.tag == "id_info":
                for child in node.findall("nct_id"):
                    self.nlmId = getStrippedTextContent(child).upper()
            elif node.tag == "brief_title":
                briefTitle = getStrippedTextContent(node)
            elif node.tag == "official_title":
                officialTitle = getStrippedTextContent(node)
            elif node.tag == "overall_status":
                self.status = getStrippedTextContent(node)
            elif node.tag == "verification_date":
                self.verified = getStrippedTextContent(node)
            elif node.tag == "lastchanged_date":
                self.lastChanged = getStrippedTextContent(node)
            elif node.tag == "phase":
                self.phase = getStrippedTextContent(node)
        self.title = officialTitle or briefTitle
        if self.nlmId:
            row = None
            try:
                cursor.execute("""\
                    SELECT xml, cdr_id, disposition, became_active
                      FROM ctgov_import
                     WHERE nlm_id = ?""", self.nlmId, timeout=TIMEOUT)
                row = cursor.fetchone()
            except Exception, e:
                msg = ("Failure selecting from ctgov_import for %s\n"
                       % self.nlmId)
                reportFailure(msg)
            if row:
                (self.oldXml, cdrId, self.disposition,
                 self.becameActive) = row
                if cdrId:

                    # If the CDR document is not a CTGovProtocol document
                    # (which generally means that it's an InScopeProtocol
                    # document), then we'll remove the CDR ID from the
                    # ctgov_import table and have the trial imported
                    # as a new CDR document. Confirmed with William O-P
                    # 2015-04-13 on a phone call.
                    cursor.execute("""\
                        SELECT a.active_status
                          FROM all_docs a
                          JOIN doc_type t
                            ON t.id = a.doc_type
                         WHERE a.id = ?
                           AND t.name = 'CTGovProtocol'""", cdrId)
                    rows = cursor.fetchall()
                    if rows:
                        self.cdrId = cdrId
                        self.activeStatus = rows[0][0].upper()

            # Added for OCECDR-4120 report.
            if self.recruiting():
                if self.becameActive is None:
                    self.becameActive = datetime.date.today()
            else:
                self.becameActive = None

    def recruiting(self):
        "Active as defined by requirements for OCECDR-4120 report."
        return self.status.lower() in Doc.activeStatuses

    def wanted(self):
        return self.status.lower() in Doc.wantedStatuses

    def block(self):
        try:
            comment = "blocking trial with status %s" % repr(self.status)
            cdr.setDocStatus(session, self.cdrId, "I", comment=comment)
            log("blocking %s (CDR%s) with status %s\n" % (repr(self.nlmId),
                                                          repr(self.cdrId),
                                                          repr(self.status)))
        except Exception, e:
            log("failure blocking %s (CDR%s): %s\n" % (repr(self.nlmId),
                                                       repr(self.cdrId), e))

    def unblock(self):
        try:
            comment = "unblocking trial with status %s" % repr(self.status)
            cdr.setDocStatus(session, self.cdrId, "A", comment=comment)
            log("unblocking %s (CDR%s) with status %s\n" % (repr(self.nlmId),
                                                            repr(self.cdrId),
                                                            repr(self.status)))
        except Exception, e:
            log("failure unblocking %s (CDR%s): %s\n" % (repr(self.nlmId),
                                                         repr(self.cdrId), e))

#----------------------------------------------------------------------
# Find out whether we should force re-importing of trial documents
# even when they are unchanged (because we want changed logic to
# be applied to the processing of the trial documsnts even if the
# the documents themselves haven't changed).
#----------------------------------------------------------------------
def loadForceReimportFlag(cursor):
    cursor.execute("""\
        SELECT val
          FROM ctl
         WHERE grp = 'ctrp'
           AND name = 'force-reimport'
           AND inactivated IS NULL""")
    rows = cursor.fetchall()
    return rows and rows[0][0] and True or False

#----------------------------------------------------------------------
# Get the latest new set of trials from CTRP.
#----------------------------------------------------------------------
def fetchTrialSet(cursor):
    try:
        os.makedirs(DIR)
        log("Created %s\n" % DIR)
    except:
        pass
    try:
        os.chdir(DIR)
        log("CWD is now %s\n" % DIR)
    except Exception, e:
        reportFailure("Unable to change to %s: %s\n" % (DIR, e))
    date = datetime.date.today()
    day = datetime.timedelta(1)
    cursor.execute("SELECT MAX(filename) FROM ctrp_trial_set")
    rows = cursor.fetchall()
    if rows and rows[0][0]:
        previous = rows[0][0].upper()
    else:
        lastWeek = date - datetime.timedelta(7)
        previous = (FILENAME % lastWeek).upper()
    filename = FILENAME % date
    while filename.upper() > previous:
        url = "%s?date=%s" % (BASE, filename)
        try:
            response = requests.get(url)
            doc = response.content
            code = response.status_code
            if code == 200:
                fp = open(filename, "wb")
                fp.write(doc)
                fp.close()
                if zipfile.is_zipfile(filename):
                    log("Fetched %s\n" % url)
                    return filename
                log("%s: not a zipfile\n" % url)
            else:
                log("%s: HTTP code %s\n" % (url, code))
        except Exception, e:
            log("Fetching %s: %s\n" % (url, e))
        date -= day
        filename = FILENAME % date
    reportFailure("No new trial set available\n", False)

#----------------------------------------------------------------------
# Connect to the database and load the trial disposition values.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect()
    cursor = conn.cursor()
    dispositions = Dispositions(cursor)
except Exception, e:
    reportFailure("Intialization failure: %s\n" % e)

#----------------------------------------------------------------------
# Decide whether we're really downloading or working from an existing
# archive.
#----------------------------------------------------------------------
if len(sys.argv) > 1:
    name = sys.argv[1]
    newTrialSet = None
else:
    name = newTrialSet = fetchTrialSet(cursor)
try:
    fp       = open(name, "rb")
    file     = zipfile.ZipFile(fp)
    nameList = file.namelist()
except Exception, e:
    msg = "Failure opening %s: %s\n" % (name, str(e))
    reportFailure(msg)
stats          = Stats()
docsInSet      = set()
wantedDocs     = set()
processDropped = True
when           = datetime.date.today().strftime("%Y-%m-%d")
forceReimport  = loadForceReimportFlag(cursor)
normalizer     = Normalizer(cursor)

# If we're testing from the command line for a subset of documents,
# we don't want to pay any attention to missing trials.
if len(sys.argv) > 2 and "PARTIAL" in sys.argv[2].upper():
    processDropped = False

#----------------------------------------------------------------------
# Walk through the archive and process each document in it.
#----------------------------------------------------------------------
try:
    for name in nameList:
        xmlFile = file.read(name)
        doc = Doc(xmlFile, name)

        #------------------------------------------------------------------
        # Note that this trial hasn't been dropped by CTRP.
        #------------------------------------------------------------------
        if processDropped and doc.nlmId:
            docsInSet.add(doc.nlmId)

        #------------------------------------------------------------------
        # If there's no NCT ID, there's not much we can do with the trial.
        #------------------------------------------------------------------
        if not doc.nlmId:
            log("Skipping document without NLM ID\n")

        #------------------------------------------------------------------
        # If the trial has a status we're not interested in, make sure
        # it's blocked.
        #------------------------------------------------------------------
        elif not doc.wanted():
            stats.closed += 1
            log("Skipping %s with status %s\n" % (repr(doc.nlmId),
                                                  repr(doc.status)))
            if doc.activeStatus == "A":
                doc.block()

        #------------------------------------------------------------------
        # Don't bother with a trial whose document has no title.
        #------------------------------------------------------------------
        elif not doc.title:
            log("Skipping %s, which has no title\n" % doc.nlmId)

        #------------------------------------------------------------------
        # Handle the documents we've already got.
        #------------------------------------------------------------------
        elif doc.disposition:

            #--------------------------------------------------------------
            # Remember CDR document IDs for the trials we want to publish,
            # so the documents don't get blocked when CTRP drops another
            # trial document which has been linked to the same CDR ID.
            #--------------------------------------------------------------
            if doc.cdrId:
                wantedDocs.add(doc.cdrId)

            #--------------------------------------------------------------
            # If nothing has changed, don't do anything but log it.
            #--------------------------------------------------------------
            if not forceReimport and not compareXml(doc.oldXml, doc.xmlFile):
                if doc.activeStatus == "A":
                    log("Skipping %s (already imported, unchanged at CTRP)\n"
                        % doc.nlmId)
                    stats.unchanged += 1
                    continue

            #--------------------------------------------------------------
            # Make sure the document isn't blocked.
            #--------------------------------------------------------------
            if doc.activeStatus == "I":
                doc.unblock()

            #--------------------------------------------------------------
            # Queue the trial document for (re-)importing. Note that the
            # cdrId member of the doc object might be None, in which
            # case we'll null out the cdr_id column. This would happen
            # with a CDR ID which linked to an old InScopeProtocol doc.
            #--------------------------------------------------------------
            disp = dispositions.codes["import requested"]
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
                           dropped = 'N',
                           phase = ?,
                           became_active = ?,
                           cdr_id = ?
                     WHERE nlm_id = ?""",
                               (doc.title[:255],
                                doc.xmlFile,
                                disp,
                                doc.verified,
                                doc.lastChanged,
                                doc.phase,
                                doc.becameActive,
                                doc.cdrId,
                                doc.nlmId), timeout=TIMEOUT)
                conn.commit()
                stats.updates += 1
                log("Queued %s for import\n" % repr(doc.nlmId))
            except Exception, info:
                log("Failure updating %s: %s\n" % (doc.nlmId, info))

        #------------------------------------------------------------------
        # Process new trials.
        #------------------------------------------------------------------
        else:

            # CIAT won't be deciding which trials to import any more.
            disp = dispositions.codes['import requested']
            try:
                cursor.execute("""\
    INSERT INTO ctgov_import (nlm_id, title, xml, downloaded, became_active,
                              disposition, dt, verified, changed, phase)
         VALUES (?, ?, ?, GETDATE(), ?, ?, GETDATE(), ?, ?, ?)""",
                               (doc.nlmId,
                                doc.title[:255],
                                doc.xmlFile,
                                doc.becameActive,
                                disp,
                                doc.verified,
                                doc.lastChanged,
                                doc.phase), timeout=TIMEOUT)
                conn.commit()
                stats.newTrials += 1
                log("Added %s with disposition import requested\n" % doc.nlmId)
            except Exception, info:
                log("Failure inserting %s: %s\n" % (doc.nlmId, str(info)))
except Exception, e:
    reportFailure("Failure in main CTGov download loop: %s\n" % e)

#----------------------------------------------------------------------
# Find out which trials are no longer being sent by CTRP.
#----------------------------------------------------------------------
try:
    droppedDocs = {}
    if processDropped:
        class DroppedDoc:
            def __init__(self, nlmId, cdrId, disposition):
                self.nlmId       = nlmId
                self.cdrId       = cdrId
                self.disposition = disposition
        cursor.execute("""\
         SELECT i.nlm_id, i.disposition, i.cdr_id, i.dropped, a.active_status
           FROM ctgov_import i
LEFT OUTER JOIN all_docs a
             ON a.id = i.cdr_id""", timeout=TIMEOUT)
        for nlmId, dispId, cdrId, dropped, activeStatus in cursor.fetchall():
            if nlmId.upper() not in docsInSet:
                newDropped = "Y"
                dispName = dispositions.names[dispId]
                if dropped != "Y":
                    droppedDocs[nlmId] = DroppedDoc(nlmId, cdrId, dispName)
                if dispName != "duplicate":
                    if activeStatus == "A" and cdrId not in wantedDocs:
                        why = "blocking dropped trial %s" % repr(nlmId)
                        try:
                            cdr.setDocStatus(session, cdrId, "I", comment=why)
                            log("%s\n" % why)
                        except Exception, e:
                            log("failure %s\n" % why)
            else:
                newDropped = "N"
            if newDropped != dropped:
                try:
                    cursor.execute("""\
                UPDATE ctgov_import
                   SET dropped = ?
                 WHERE nlm_id = ?""", (newDropped, nlmId), timeout=TIMEOUT)
                    conn.commit()
                except Exception, e:
                    log("Failure setting dropped flag to %s for %s: %s\n",
                        (repr(newDropped), nlmId, e))
except Exception, e:
    reportFailure("Failure processing dropped documents: %s\n" % e)

#----------------------------------------------------------------------
# Record successful processing of the set if it's newly downloaded.
#----------------------------------------------------------------------
if newTrialSet:
    cursor.execute("""\
INSERT INTO ctrp_trial_set (filename, processed)
     VALUES (?, GETDATE())""", newTrialSet)
    conn.commit()

#----------------------------------------------------------------------
# Log the download statistics.
#----------------------------------------------------------------------
totals = stats.totals()
try:
    log("                 New trials: %5d\n" % stats.newTrials)
    log("             Updated trials: %5d\n" % stats.updates)
    log("   Skipped unchanged trials: %5d\n" % stats.unchanged)
    log("      Skipped closed trials: %5d\n" % stats.closed)
    log("               Total trials: %5d\n" % totals)
    cursor.execute("""\
        INSERT INTO ctgov_download_stats (dt, total_trials, new_trials,
                                          transferred,
                                          updated, unchanged, pdq_cdr,
                                          duplicates, out_of_scope, closed)
             VALUES (?, ?, ?, 0, ?, ?, 0, 0, 0, ?)""",
                   (when, totals, stats.newTrials, stats.updates,
                    stats.unchanged, stats.closed), timeout=TIMEOUT)
    conn.commit()
except Exception, e:
    log("Failure logging download statistics: %s\n" % e, True)

#----------------------------------------------------------------------
# Send out an immediate email report.
#----------------------------------------------------------------------
try:
    subject = "CTGov trials downloaded %s on %s" % (when, server)
    recips  = getEmailRecipients(cursor)
    if recips:
        body = """\
                                New trials: %5d
                            Updated trials: %5d
                  Skipped unchanged trials: %5d
       Skipped closed and completed trials: %5d
                              Total trials: %5d

    """ % (stats.newTrials, stats.updates, stats.unchanged, stats.closed,
           totals)
        if droppedDocs:
            for key in sorted(droppedDocs):
                droppedDoc = droppedDocs[key]
                if droppedDoc.cdrId:
                    body += """\
    Trial %s [disposition %s] (imported as CDR%d) dropped by NLM.
    """ % (droppedDoc.nlmId, repr(droppedDoc.disposition), droppedDoc.cdrId)
                else:
                    body += """\
    Trial %s [disposition %s] dropped by NLM.
    """ % (droppedDoc.nlmId, repr(droppedDoc.disposition))
        sendReport(recips, subject, body)
        log("Mailed download stats to %s\n" % str(recips))
    else:
        log("Warning: no email addresses found for report\n")
except Exception, e:
    log("Failure sending out CT.gov download report: %s\n" % e, True)
cdr.logout(session)
