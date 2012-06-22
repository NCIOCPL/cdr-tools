#----------------------------------------------------------------------
#
# $Id$
#
# Retrieve sets of trials from CTRP and queue them for import.
#
# See https://trials.nci.nih.gov/pa/pdqgetAvailableFiles.action
# for list of trial sets currently available for retrieval.
#
#----------------------------------------------------------------------
import cdrdb, lxml.etree as etree, sys, urllib2, zipfile, cdr, os, datetime
import re

RSS = "CTEPRSS RSS"
BASE = "https://trials.nci.nih.gov/pa/pdqgetFileByDate.action"
BASE = "https://trials-qa.nci.nih.gov/pa/pdqgetFileByDate.action"
LOGFILE = cdr.DEFAULT_LOGDIR + "/DownloadCtrpTrials.log"
CTRP = 'CTRP (Clinical Trial Reporting Program)'
IMPORT = 'import requested'

#----------------------------------------------------------------------
# Write a message to the console and to the job's log file.
#----------------------------------------------------------------------
def log(me):
    sys.stderr.write("%s\n" % me)
    cdr.logwrite(me, LOGFILE)

#----------------------------------------------------------------------
# Object representing a value used to identify a CTRP trial.
#----------------------------------------------------------------------
class TrialID:
    def __init__(self, node):
        self.value = self.domain = self.type = None
        for child in node:
            if child.tag == 'id':
                self.value = child.text
            elif child.tag == 'id_type':
                self.type = child.text
            elif child.tag == 'id_domain':
                self.domain = child.text

#----------------------------------------------------------------------
# One of these for each trial document we download from CTRP.
#----------------------------------------------------------------------
class Trial:
    def __init__(self, archive, docName, cursor):
        self.name = docName
        self.owners = set()
        self.ctrpId = self.nctId = self.cdrId = self.lastXml = self.disp = None
        try:
            xmlDoc = archive.read(docName)
        except Exception, e:
            message = "Failure reading %s: %s" % (docName, repr(e))
            raise Exception(message)
        try:
            self.tree = etree.fromstring(xmlDoc)
            self.xmlDoc = unicode(xmlDoc, 'utf-8')
        except Exception, e:
            message = "Failure parsing %s: %s" % (docName, repr(e))
            raise Exception(message)
        if self.tree.tag != 'clinical_study':
            message = "%s is not a clinical study" % docName
            raise Exception(message)
        for owner in self.tree.findall('trial_owners/name'):
            self.owners.add(owner.text)
        if self.inScope():
            for node in self.tree.findall('id_info/secondary_id'):
                trialId = TrialID(node)
                if trialId.domain == 'NCT':
                    self.nctId = trialId.value
                elif trialId.domain == CTRP:
                    self.ctrpId = trialId.value
            cursor.execute("""\
SELECT i.cdr_id, i.doc_xml, d.disp_name
  FROM ctrp_import i
  JOIN ctrp_import_disposition d
    ON d.disp_id = i.disposition
 WHERE i.ctrp_id = ?""", self.ctrpId)
            for cdrId, docXml, disp in cursor.fetchall():
                self.cdrId = cdrId
                self.lastXml = docXml
                self.disp = disp
            if not self.cdrId:
                cdrIds = set()
                cursor.execute("""\
SELECT doc_id
  FROM query_term
 WHERE path IN ('/CTGovProtocol/IDInfo/OrgStudyId',
                '/CTGovProtocol/IDInfo/SecondaryID')
   AND value = ?""", self.ctrpId)
                for row in cursor.fetchall():
                    cdrIds.add(row[0])
                if len(cdrIds) > 1:
                    raise Exception("multiple matches for %s: %s" %
                                    (repr(self.ctrpId), repr(cdrIds)))
                if cdrIds:
                    self.cdrId = cdrIds.pop()

    #------------------------------------------------------------------
    # Has CTRP changed the document since we last downloaded it?  May
    # make the comparison more sophisticated at some point later on.
    #------------------------------------------------------------------
    def unchanged(self):
        return self.xmlDoc == self.lastXml

    #------------------------------------------------------------------
    # We're only interested in the trial's sites if RSS is maintaining
    # them, in which case they'll be listed as one of the owners of the
    # trial.
    #------------------------------------------------------------------
    def inScope(self):
        return RSS in self.owners

    #------------------------------------------------------------------
    # Create or update a row in the ctrp_import table marking this
    # trial as ready to have its site information imported into the
    # corresponding CTGovProtocol document.
    #------------------------------------------------------------------
    def queue(self, cursor, disposition):
        if self.lastXml:
            cursor.execute("""\
UPDATE ctrp_import
   SET doc_xml = ?,
       disposition = ?
 WHERE ctrp_id = ?""", (self.xmlDoc, disposition, self.ctrpId))
        else:
            cursor.execute("""\
INSERT INTO ctrp_import (ctrp_id, disposition, cdr_id, nct_id, doc_xml)
     VALUES (?, ?, ?, ?, ?)""", (self.ctrpId, disposition, self.cdrId,
                                 self.nctId, self.xmlDoc))

#----------------------------------------------------------------------
# Download the set of clinical trial documents created on the date
# specified by the caller.
#----------------------------------------------------------------------
class TrialSet:
    def __init__(self, date, conn):

        # Initialize object members.
        self.inScope = self.processed = self.new = self.changed = 0
        self.failures = self.unchanged = self.outOfScope = self.unmatched = 0
        self.conn = conn
        self.cursor = conn.cursor()
        self.date = date
        self.filename = TrialSet.makeFilename(date)
        self.url = "%s?date=%s" % (BASE, self.filename)

        # Fetch the compressed archive containing the trial documents.
        try:
            server = urllib2.urlopen(self.url)
            doc = server.read()
        except Exception, e:
            message = "Failure retrieving %s: %s" % (url, repr(e))
            log(message)
            raise cdr.Exception(message)

        # Store the archive in the local file system.
        try:
            fp = open(self.filename, "wb")
            fp.write(doc)
            fp.close()
        except Exception, e:
            message = "Failure storing %s: %s" % (self.filename, repr(e))
            log(message)
            raise cdr.Exception(message)

        # Wrap the archive file with an object which lets us read the docs.
        try:
            fp = open(self.filename, "rb")
            self.archive = zipfile.ZipFile(fp)
            self.nameList = self.archive.namelist()
        except Exception, e:
            message = "Failure opening %s: %s" % (self.filename, repr(e))
            log(message)
            raise cdr.Exception(message)

        # Create the download job.
        self.cursor.execute("""\
INSERT INTO ctrp_download_job (downloaded, job_filename, job_url)
     VALUES (GETDATE(), ?, ?)""", (self.filename, self.url))
        self.cursor.execute("SELECT @@IDENTITY")
        self.jobId = int(self.cursor.fetchall()[0][0])
        log("Job %d (%s)" % (self.jobId, self.filename))

    #------------------------------------------------------------------
    # Process the trials in the downloaded archive.  Record the
    # disposition for each one.  Possible dispositions include:
    #
    # out of scope - not maintained by RSS, so we're not interested
    # unmatched    - in scope, but we can't find a corresponding CDR doc
    # new          - in scope, with a match; hasn't been queued before
    # unchanged    - the doc is unchanged from what we queued last time
    # changed      - doc has changed since we last queued it
    # failure      - we can't even parse the document to learn more
    #
    #------------------------------------------------------------------
    def queueTrials(self):

        # Get database IDs for dispositions we'll set.
        self.dispositions = TrialSet.loadDispositions(self.cursor)
        self.importRequested = TrialSet.loadImportDisposition(IMPORT,
                                                              self.cursor)

        # Loop through the trial documents in the set.
        log("%d files in archive" % len(self.nameList))
        for docName in self.nameList:

            # Don't bother with anything that's not an XML document.
            if docName.lower().endswith(".xml"):

                # Use the trial ID extracted from the file, since we
                # might have to record events for documents we can't
                # parse.
                trialId = docName[:-4].upper()
                try:

                    # Parse the document.
                    self.processed += 1
                    trial = Trial(self.archive, docName, self.cursor)

                    # Determine the trials disposition.
                    if trial.inScope():
                        self.inScope += 1
                    else:
                        self.recordTrial(trialId, 'out of scope')
                        self.outOfScope += 1
                        continue
                    if trial.lastXml:
                        if trial.unchanged():
                            self.unchanged += 1
                            self.recordTrial(trialId, 'unchanged')
                        else:
                            self.changed += 1
                            trial.queue(self.cursor, self.importRequested)
                            self.recordTrial(trialId, 'changed')
                    elif trial.cdrId:
                        self.new += 1
                        trial.queue(self.cursor, self.importRequested)
                        self.recordTrial(trialId, 'new')
                    else:
                        self.unmatched += 1
                        self.recordTrial(trialId, 'unmatched')
                except Exception, e:
                    self.failures += 1
                    self.recordTrial(trialId, 'failure', str(e))
                    log(str(e))
        self.log()
        self.conn.commit()

    #------------------------------------------------------------------
    # Record counts of processing outcomes.  Calls the global log().
    #------------------------------------------------------------------
    def log(self):
        log("     total trials downloaded: %d" % self.processed)
        log("       RSS trials downloaded: %d" % self.inScope)
        log("   non-RSS trials downloaded: %d" % self.outOfScope)
        log("       new RSS trials queued: %d" % self.new)
        log("   changed RSS trials queued: %d" % self.changed)
        log("unchanged RSS trials skipped: %d" % self.unchanged)
        log("unmatched RSS trials skipped: %d" % self.unmatched)
        log("    trials failed processing: %d" % self.failures)
 
    #------------------------------------------------------------------
    # Create the string for a download set using a format we can
    # predict.  Relies on the fact that the __str__() method of
    # the datetime.date object passed in produces a string in the
    # expected ISO format of YYYY-MM-DD.
    #------------------------------------------------------------------
    @staticmethod
    def makeFilename(date):
        return "CTRP-TRIALS-%s.zip" % date

    #------------------------------------------------------------------
    # Determine the date of the last successful downloaded set.
    #------------------------------------------------------------------
    @staticmethod
    def getLastSetDate(cursor):
        cursor.execute("SELECT MAX(job_filename) FROM ctrp_download_job")
        rows = cursor.fetchall()
        if not rows:
            return None
        match = re.match(r"CTRP-TRIALS-(\d\d\d\d)-(\d\d)-(\d\d)\.zip",
                         rows[0][0])
        if not match:
            raise Exception("unexpected filename format for last set date: %s"
                            % repr(rows[0][0]))
        return datetime.date(int(match.group(1)),
                             int(match.group(2)),
                             int(match.group(3)))
        
    #------------------------------------------------------------------
    # Generate a map of download disposition strings to the IDs for
    # those disposition values.
    #------------------------------------------------------------------
    @staticmethod
    def loadDispositions(cursor):
        cursor.execute("""\
    SELECT disp_id, disp_name
      FROM ctrp_download_disposition""")
        dispositions = {}
        for dispId, dispName in cursor.fetchall():
            dispositions[dispName] = dispId
        return dispositions

    #------------------------------------------------------------------
    # Fetch the ID which corresponds to the named disposition from
    # the ctrp_import_disposition table.
    #------------------------------------------------------------------
    @staticmethod
    def loadImportDisposition(name, cursor):
        cursor.execute("""\
SELECT disp_id
  FROM ctrp_import_disposition
 WHERE disp_name = ?""", name)
        return cursor.fetchall()[0][0]

    #------------------------------------------------------------------
    # Remember what we decided to do with a particular trial during
    # the current download job.
    #------------------------------------------------------------------
    def recordTrial(self, trialId, disposition, comment=None):
        log("%s: %s" % (repr(trialId), disposition))
        self.cursor.execute("""\
INSERT INTO ctrp_download (job_id, ctrp_id, disposition, comment)
     VALUES (?, ?, ?, ?)""", (self.jobId, trialId,
                              self.dispositions[disposition], comment))

#----------------------------------------------------------------------
# Create the download directory if it doesn't already exist, and
# move the that directory, making it the default location for all
# subsequent processing.
#----------------------------------------------------------------------
def moveToDownloadDirectory():
    curdir = os.getcwd()
    downloadDirectory = os.path.join(curdir, "CTRPDownloads")
    try:
        os.makedirs(downloadDirectory)
    except:
        pass
    os.chdir(downloadDirectory)
    log("CWD: '%s'" % downloadDirectory)

#----------------------------------------------------------------------
# Walk backwards in time, looking for the most recent trial set
# available from CTRP.  Unfortunately, they actually told us they
# were unable to implement a simple service which would tell us
# which sets were available!  So we have to do this the brute force
# way.  Also unfortunate: they're unable (unwilling?) to return an
# HTTP error code if asked for a set which doesn't exist, and instead
# they give us back a valid HTML document in response to such a
# request.  We have to rely on the failure of the attempt to
# process the zipfile to tell us that no such set exists.  Makes
# it difficult to distinguish between this condition and other
# conditions, such as a corrupted file.  Oh, well.
#
# We stop trying to get a set if we reach the date for a set we've
# already successfully retrieved, or if we've gone back so far that
# we should just give up.
#
# Optionally, the invoker of the script can force the program to
# download and process the set for a specific date.  This would
# be useful if we thought the download of a particular set was
# successful, and then we discover that it was incomplete, or
# had some other problem and had to be downloaded and processed
# again.  We'll need to think carefully about the particular
# circumstances whenever we do that, to make sure we're not
# creating problems with (for example) partially processed documents
# within such a batch.
#
# We should schedule this job for shortly before midnight, so we
# don't waste time looking for a set they haven't had time to generate
# yet.
#----------------------------------------------------------------------
def main():
    moveToDownloadDirectory()
    conn = cdrdb.connect()
    cursor = conn.cursor()
    if len(sys.argv) > 1:
        log("invoked for explicit download of %s" % sys.argv[1])
        try:
            trialSet = TrialSet(sys.argv[1], conn)
            trialSet.queueTrials()
        except Exception, e:
            log("%s: %s" % (sys.argv[1], e))
    else:
        date = datetime.date.today()
        oneDay = datetime.timedelta(1)
        oneWeek = datetime.timedelta(7)
        threshold = date - oneWeek
        lastSetDate = TrialSet.getLastSetDate(cursor)
        if lastSetDate and lastSetDate > threshold:
            threshold = lastSetDate
        log("looking for trial sets after %s" % threshold)
        while date > threshold:
            try:
                trialSet = TrialSet(date, conn)
                trialSet.queueTrials()
                return
            except Exception, e:
                log("%s: %s" % (date, e))
                date -= oneDay
        log("no new sets found to be downloaded")

#----------------------------------------------------------------------
# Run the script if we're not being loaded as an included module.
#----------------------------------------------------------------------
if __name__ == "__main__":
    main()
