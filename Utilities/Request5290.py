#----------------------------------------------------------------
# $Id$
#
# Copy the PurposeText element from each Health Professional Summary
# to its corresponding Patient Summary, if there is one.
#
# Parameters:
#   UserID, password, mode ('test' or 'live'), maxDocs
#
# BZIssue::5029
#
#                                           Alan Meyer
#                                           May, 2013
#----------------------------------------------------------------
import sys, lxml.etree as lx, cdr, cdrdb, ModifyDocs

class OneOffGlobal:
    """
    All code for this transformation is here.
    """

    def __init__(self):
        """
        XXX May not need anything
        """

    def log(self, patId, hpId, msg):
        """
        Log a message pertaining to a Summary pair.

        Pass:
            patId - CDR ID of the Patient Summary
            hpId  - CDR ID of the corresponding HP Summary
            msg   - Text of the message to log
        """
        if not patId:
            patId = 'None'
        if not hpId:
            hpId = 'None'
        logMsg = "PatientSumID=%s  HPSumID=%s: %s" % (patId, hpId, msg)

        # Use the ModifyDocs log function to put this message in context
        self.job.log(logMsg)

    def getDocIds(self):

        # Find all Patient Summaries with active status = 'A'
        # Picks up both English and Spanish
        qry = """
            SELECT id
              FROM document
             WHERE active_status = 'A'
               AND id IN (
            SELECT doc_id
              FROM query_term
             WHERE path = '/Summary/SummaryMetaData/SummaryAudience'
               AND value = 'Patients'
            )
             ORDER BY id"""

        try:
            conn = cdrdb.connect()
            cursor = conn.cursor()
            cursor.execute(qry)
            rows = cursor.fetchall()
            cursor.close()
        except cdrdb.Error as info:
            self.job.log("Database error selecting ids: %s" % str(info))
            sys.exit(1)

        # Save and return them
        self.docIds = [row[0] for row in rows]
        return self.docIds

    def run(self, ptDocObject):
        # Append this to log message if no changes are made
        NO_CHG = ", no changes made"

        # This is what we're going to copy.  Don't have it yet
        purposeText = None

        # Parse the Patient Summary xml
        ptRoot = lx.fromstring(ptDocObject.xml)

        # Is there already a PurposeText?  If so, nothing to do
        purposeElems = ptRoot.xpath("/Summary/SummaryMetaData/PurposeText")
        if purposeElems:
            # Already there
            self.log(ptDocObject.id, None,
                "Patient Summary already has PurposeText" + NO_CHG)
            # Return unchanged XML.  ModifyDocs will not store it
            return ptDocObject.xml

        # Locate the corresponding HP Summary
        hpRef = ptRoot.xpath('/Summary/PatientVersionOf')
        if not hpRef:
            # T'weren't there
            self.log(ptDocObject.id, None,
                "Patient Summary has no PatientVersionOf element, "
                "no changes made")
            # Return unchanged XML.  ModifyDocs will not store it
            return ptDocObject.xml

        # Look for the cdr:ref identifying the HP Summary
        try:
            hpRefId = hpRef[0].attrib['{cips.nci.nih.gov/cdr}ref']
        except KeyError:
            # Log issue and return unchanged xml
            self.log(ptDocObject.id, None,
                "Patient Summary PatientVersionOf missing cdr:ref")
            return ptDocObject.xml

        # Get the PurposeText
        hpDocObject = cdr.getDoc(job.session, hpRefId, getObject=True)
        hpRoot = lx.fromstring(hpDocObject.xml)
        # hpRoot = hpTree.getroot()
        purposeElem = hpRoot.xpath("/Summary/SummaryMetaData/PurposeText")
        if not purposeElem:
            # Report and return unchanged
            self.log(ptDocObject.id, hpDocObject.id,
                "HP Summary missing PurposeText")
            return ptDocObject.xml

        purposeText = purposeElem[0].text
        if not purposeText:
            self.log(ptDocObject.id, hpDocObject.id,
                "HP Summary has PurposeText element, but no text")
            return ptDocObject.xml

        # Create an element to put into the PtSummary
        ptPurposeText = lx.Element("PurposeText")
        ptPurposeText.text = purposeText

        # Add it in
        metaDataElems = ptRoot.xpath("/Summary/SummaryMetaData")
        metaDataElems[0].append(ptPurposeText)

        # Return serialized xml
        newXml = lx.tostring(ptRoot)
        return newXml


if __name__ == "__main__":
    if len(sys.argv) < 4 or sys.argv[3] not in ('test', 'live'):
        sys.stderr.write("usage: Request5290.py uid pwd test|live {maxDocs}\n")
        sys.stderr.write("""
Use optional maxDocs to process a limited number of docs in order to
avoid swamping cancer.gov.
For example, the following maxDocs transforms 50 docs per run:
    50  The first 50.
   100  100 docs, but the first 50 will be skipped because they already
         have PurposeText.
   150  150 docs, but the first 100 will be skipped.
   etc.
""")
        sys.exit(1)
    uid, pwd, flag = sys.argv[1:4]

    # Optional maximum number of docs to process
    maxDocs = 999999
    if len(sys.argv) == 5:
        maxDocs = int(sys.argv[4])
        if maxDocs < 1:
            sys.stderr.write("Invalid maxDocs count of docs to process")
            sys.exit(1)

    # Boolean true = test, false = live
    testMode = (flag == 'test')

    # Debug
    # testMode = True

    obj = OneOffGlobal()
    try:
        job = ModifyDocs.Job(uid, pwd, obj, obj,
                "Copy HP Summary PurposeText to corresponding Patient Summary",
                validate=True, testMode=testMode)
    except Exception, info:
        sys.stderr.write("Exception: %s" % str(info))
        sys.exit(1)
    except:
        sys.stderr.write("An exception occurred")
        sys.exit(1)

    # Store reference to the job object in the object passed to Job.
    # This makes logging and credentials available to the logic
    obj.job = job

    # Run the job for the specified max number of docs
    job.setMaxDocs(maxDocs)
    # Debug
    # job.setMaxDocs(1)

    job.run()
    try:
        # job.run()
        pass
    except Exception, info:
        sys.stderr.write("Exception: %s" % str(info))
        sys.exit(1)
    except:
        sys.stderr.write("An exception occurred")

