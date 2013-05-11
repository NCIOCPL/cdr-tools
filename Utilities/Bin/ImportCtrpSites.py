#----------------------------------------------------------------------
#
# $Id$
#
# Script to walk the queue of CTRP trials waiting for import and merge
# the site information from those trials into the corresponding CDR
# CTGovProtocol documents.
#
# BZIssue::4942
#
#----------------------------------------------------------------------
import cdrdb, lxml.etree as etree, cgi, ctrp, cdr, sys, copy

LOGFILE = cdr.DEFAULT_LOGDIR + "/CTRPImport.log"
TESTING = True

#----------------------------------------------------------------------
# Object used to track what we do for this import job.
#----------------------------------------------------------------------
class ImportJob:

    #------------------------------------------------------------------
    # Member of the job's queue.
    #------------------------------------------------------------------
    class Trial:
        def __init__(self, ctrpId, cdrId):
            self.ctrpId = ctrpId
            self.cdrId = cdrId

    #------------------------------------------------------------------
    # Prepare for processing the queue of CTRP imports.
    #------------------------------------------------------------------
    def __init__(self):

        # Initialize some counters for reporting.
        self.imported = self.locked = self.failures = 0

        # Load the CTRP mappings used to find gaps which would prevent import.
        self.poIds = ctrp.getPoidMappings()
        self.geoMap = ctrp.GeographicalMappings()

        # Log into the CDR so we can update the mapping table and the docs.
        self.session = cdr.login("ExternalImporter", "***REMOVED***")

        # Load the queue.
        self.conn = cdrdb.connect()
        self.cursor = self.conn.cursor()
        self.cursor.execute("""\
  SELECT i.ctrp_id, i.cdr_id
    FROM ctrp_import i
    JOIN ctrp_import_disposition d
      ON d.disp_id = i.disposition
   WHERE d.disp_name = 'import requested'
     AND i.cdr_id IS NOT NULL
     AND i.doc_xml IS NOT NULL
ORDER BY i.ctrp_id""")
        self.queue = [self.Trial(r[0], r[1]) for r in self.cursor.fetchall()]
        self.log("%d CTRP trials queued for site import" % len(self.queue))

        # Load the ID for the disposistion "import requested" (optimization).
        self.cursor.execute("""\
SELECT disp_id
  FROM ctrp_import_disposition
 WHERE disp_name = 'imported'""")
        self.importedDisposition = self.cursor.fetchall()[0][0]

        # Create the job and fetch its ID.
        if not TESTING:
            self.cursor.execute("""\
INSERT INTO ctrp_import_job (imported)
     VALUES (GETDATE())""")
            self.conn.commit()
            self.cursor.execute("SELECT @@IDENTITY")
            self.jobId = self.cursor.fetchall()[0][0]
        else:
            self.jobId = 0

    #------------------------------------------------------------------
    # Add a row to the ctrp_import_event table for a trial whose site
    # information we cannot import because another user has the CDR
    # CTGovProtocol document locked.
    #------------------------------------------------------------------
    def recordLockedDoc(self, ctrpId):
        self.log("Trial '%s' skipped (locked by another user)" % ctrpId)
        self.locked += 1
        if TESTING:
            return
        self.cursor.execute("""\
INSERT INTO ctrp_import_event (job_id, ctrp_id, locked)
     VALUES (?, ?, 'Y')""", (self.jobId, ctrpId))
        self.conn.commit()

    #------------------------------------------------------------------
    # Add a row to the ctrp_import_event table for a trial whose site
    # information we cannot import because of holes in the mappings
    # of persons, organizations, countries, and/or political subdivisions.
    #------------------------------------------------------------------
    def recordMappingGaps(self, ctrpId):
        self.log("Trial '%s' skipped (mapping problems)" % ctrpId)
        self.failures += 1
        if TESTING:
            return
        self.cursor.execute("""\
INSERT INTO ctrp_import_event (job_id, ctrp_id, mapping_gaps)
     VALUES (?, ?, 'Y')""", (self.jobId, ctrpId))
        self.conn.commit()

    #------------------------------------------------------------------
    # Add a row to the ctrp_import_event table for a trial whose site
    # information we have imported, and update the disposition for the
    # trial so that it's no longer in the import queue.
    #------------------------------------------------------------------
    def recordImportEvent(self, ctrpId):
        self.imported += 1
        if TESTING:
            return
        self.cursor.execute("""\
INSERT INTO ctrp_import_event (job_id, ctrp_id)
     VALUES (?, ?)""", (self.jobId, ctrpId))
        self.cursor.execute("""\
UPDATE ctrp_import
   SET disposition = ?
 WHERE ctrp_id = ?""", (self.importedDisposition, ctrpId))
        self.conn.commit()

    #------------------------------------------------------------------
    # Fetch the document for a CTRP trial document from the import table.
    #------------------------------------------------------------------
    def loadCtrpDoc(self, trial):
        self.cursor.execute("SELECT doc_xml FROM ctrp_import WHERE ctrp_id = ?",
                            trial.ctrpId)
        return etree.XML(self.cursor.fetchall()[0][0].encode("utf-8"))

    #------------------------------------------------------------------
    # Pass-through to the routine in the ctrp module which identifies
    # persons, organizations, countries, or political subdivisions for
    # which we will be unable to find the corresponding CDR documents,
    # preventing import of the CTRP trial's site information.
    #------------------------------------------------------------------
    def findMappingProblems(self, doc):
        return ctrp.MappingProblem.findMappingProblems(self.session, doc,
                                                       self.poIds, self.geoMap,
                                                       orgsOnly=True)

    #------------------------------------------------------------------
    # Create an entry in the log file for the script, and show the
    # entry on the console.
    #------------------------------------------------------------------
    @staticmethod
    def log(what):
        sys.stderr.write("%s\n" % what)
        if not TESTING:
            cdr.logwrite(what, LOGFILE)

#----------------------------------------------------------------------
# Examine the CDR server's response to a request to version a document.
# That response will be represented by a tuple containing the CDR ID
# as the first element and the (possibly empty) sequence of errors and
# warnings reported as the second element.  If the first element does
# not contain the CDR ID, then the request completely failed, so we
# raise an exception.  Otherwise we log any warnings from the second
# element of the server's response.
#----------------------------------------------------------------------
def checkResponse(resp):
    if not resp[0]:
        errors = cdr.getErrors(resp[1], errorsExpected=True, asSequence=False)
        raise Exception(errors)
    if resp[1]:
        warnings = cdr.getErrors(resp[1], errorsExpected=False, asSequence=True)
        ImportJob.log(repr(warnings))

#----------------------------------------------------------------------
# Fold the information from the CTRP document into the CDR document
# passed in by the caller (as a utf-8 string).  If a CTRPInfo block
# is already present, replace it.  Otherwise, add the block at the
# end of the document.
#----------------------------------------------------------------------
def merge(oldXml, infoBlock):
    tree = etree.fromstring(oldXml)
    replaced = False
    for node in tree.findall("CTRPInfo"):
        tree.replace(node, copy.deepcopy(infoBlock))
        replaced = True
        break
    if not replaced:
        tree.append(copy.deepcopy(infoBlock))
    return etree.tostring(tree, xml_declaration=True, encoding="utf-8")

#----------------------------------------------------------------------
# Return True if the two versions of the XML document differ after
# normalization to eliminate whitespace or other trivial differences.
#----------------------------------------------------------------------
def compare(oldXml, newXml):
    return cmp(normalize(oldXml), normalize(newXml)) and True or False

#----------------------------------------------------------------------
# Run the XML document through the parser to eliminate whitespace
# or other insignificant differences (for example, order of attributes
# or use of character entities).
#----------------------------------------------------------------------
def normalize(docXml):
    return docXml and etree.tostring(etree.fromstring(docXml.strip()),
                                     encoding="utf-8") or ""

#----------------------------------------------------------------------
# Retrieve the XML for a CDR document from the repository.  Get the
# current working copy of the document if no version is specified;
# otherwise get the version requested.  Return None if the document
# or version is not found.
#----------------------------------------------------------------------
def getDocXml(cursor, cdrId, version=None):
    if version:
        cursor.execute("""\
SELECT xml
  FROM doc_version
 WHERE id = ?
   AND num = ?""", (cdrId, version))
    else:
        cursor.execute("SELECT xml FROM document WHERE id = ?", cdrId)
    rows = cursor.fetchall()
    return rows and rows[0][0].encode("utf-8") or None

#----------------------------------------------------------------------
# Merge site information from the CTRP document into the CTGovProtocol
# document, and create new CDR document versions as appropriate.
#----------------------------------------------------------------------
def updateDocument(job, trial, tree):

    # Record what we're planning to do.
    job.log("merging sites from CTRP trial %s into CDR%d" %
            (trial.ctrpId, trial.cdrId))

    # Check out the document for changes.
    checkout = TESTING and "N" or "Y"
    docObj = cdr.getDoc(job.session, trial.cdrId, checkout=checkout,
                        getObject=True)
    err = cdr.checkErr(docObj)
    if err:
        print err
        job.recordLockedDoc(trial.ctrpId)
        return

    # Create a new CTRPInfo block to be inserted into the CDR document.
    protocol = ctrp.Protocol(tree)
    infoBlock = protocol.makeInfoBlock(trial.ctrpId)

    # Get the XML for the CDR versions of the CTGovProtocol document
    cdrId = cdr.normalize(trial.cdrId)
    lastAny, lastPub, isChanged = cdr.lastVersions(job.session, cdrId)
    cwdXml = docObj.xml
    verXml = pubXml = None
    if lastAny > 0:
        if isChanged == 'Y':
            verXml = getDocXml(job.cursor, trial.cdrId, lastAny)
        else:
            verXml = cwdXml
    if lastPub > 0:
        job.cursor.execute("""\
SELECT t.name
  FROM doc_type t
  JOIN doc_version v
    ON v.doc_type = t.id
 WHERE v.id = ?
   AND v.num = ?""", (trial.cdrId, lastPub))
        docType = job.cursor.fetchall()[0][0]
        if docType == 'CTGovProtocol':
            if lastPub == lastAny:
                pubXml = verXml
            else:
                pubXml = getDocXml(job.cursor, trial.cdrId, lastPub)
        else:
            job.log("Skipping last pub ver (%d) of CDR%d (%s)" %
                    (lastPub, trial.cdrId, docType))

    # Fold the site information into the version(s) to be updated.
    # Could have conditionally optimized away the second call to merge(),
    # but keeping the code clean and simple trumps performance here.
    newCwdXml = merge(cwdXml, infoBlock)
    newPubXml = pubXml and merge(pubXml, infoBlock) or None
    if TESTING:
        fp = open("ctrptest-%s-cwd.xml" % trial.cdrId, "wb")
        fp.write(newCwdXml)
        fp.close()
        if newPubXml:
            fp = open("ctrptest-%s-pub.xml" % trial.cdrId, "wb")
            fp.write(newPubXml)
            fp.close()
        return

    # If the CWD has been changed since the last version, capture it.
    if compare(verXml, cwdXml):
        job.log("ImportCtrpSites: versioning CWD for CDR%d" % trial.cdrId)
        comment = 'ImportCtrpSites: preserving current working doc'
        response = cdr.repDoc(job.session, doc=str(docObj), ver='Y',
                              reason=comment, comment=comment,
                              showWarnings=True, verPublishable='N')
        checkResponse(response)

    # If the latest publishable version has changed, version it.
    comment = "importing site information from CTRP trial %s" % trial.ctrpId
    if newPubXml and compare(pubXml, newPubXml):
        job.log(("creating publishable version of CDR%d from sites in "
                 "CTRP trial %s") % (trial.cdrId, trial.ctrpId))
        docObj.xml = cwdXml = newPubXml
        response = cdr.repDoc(job.session, doc=str(docObj), ver="Y", val="Y",
                              reason=comment, comment=comment,
                              showWarnings=True)
        checkResponse(response)

    # If the new CWD has changes we haven't saved yet, version them.
    if compare(cwdXml, newCwdXml):
        job.log(("creating unpublishable version of CDR%d from sites in "
                 "CTRP trial %s") % (trial.cdrId, trial.ctrpId))
        docObj.xml = newCwdXml
        response = cdr.repDoc(job.session, doc=str(docObj), ver="Y",
                              reason=comment, comment=comment,
                              showWarnings=True, verPublishable="N")
        checkResponse(response)

    # Take this trial out of the import queue.
    job.recordImportEvent(trial.ctrpId)

#----------------------------------------------------------------------
# Collect all of the CTRP trial documents queued for import.  For each
# one, determine whether there are any mapping gaps which would prevent
# the import from succeeding.  If there are no such gaps, pull the
# site information from the CTRP document and insert that information
# into the corresponding CTGovProtocol document.
#----------------------------------------------------------------------
def main():

    # Initialize the import job, loading the queue of trials to import.
    job = ImportJob()

    # Walk through the queue, processing each CTRP trial.
    for trial in job.queue:

        try:

            # Get the CTRP document for the queued trial.
            doc = job.loadCtrpDoc(trial)

            # Import the trials sites if there are no mapping problems.
            if job.findMappingProblems(doc):
                job.recordMappingGaps(trial.ctrpId)
            else:
                fp.write("http://bach.nci.nih.gov/cgi-bin/cdr/"
                         "show-cdr-doc.py?id=%d\n" % trial.cdrId)
                fp.write("http://bach.nci.nih.gov/cgi-bin/cdr/"
                         "show-ctrp-doc.py?id=%s\n" % trial.ctrpId)
                updateDocument(job, trial, doc)

        except Exception, e:
            job.failures += 1
            job.log("Trial '%s': %s" % (trial.ctrpId, e))

        finally:
            if not TESTING:
                cdr.unlock(job.session, trial.cdrId)

    # Log the summary of what we did.
    job.log("Updated %d trials" % job.imported)
    job.log("Skipped %d trials" % (job.failures + job.locked))
    fp.close()

if __name__ == "__main__":
    if "--test" not in sys.argv and "--live" not in sys.argv:
        sys.stderr.write("usage: %s --test|--live\n" % sys.argv[0])
    else:
        TESTING = ("--test" in sys.argv)
        sys.stderr.write("running in %s mode\n" %
                         (TESTING and "test" or "live"))
        main()
