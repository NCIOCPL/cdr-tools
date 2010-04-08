#----------------------------------------------------------------------
# $Id$
#
# Global change to add "Transfer not required" to InScopeProtocols
# for which it is known that no transfer to CTGov will be required.
#
# This actually runs as five separate ModifyDocs global change jobs,
# one for each reasons for which a transfer is not required.
#
# BZIssue::4721
#----------------------------------------------------------------------
import sys, time, cdr, cdrdb, ModifyDocs

# Name of the program for logging
SCRIPT = "Request4721.py"

def fatal(msg, job=None):
    """
    Log an error and abort.

    Pass:
        msg - Error message.
        job - Reference to ModifyDocs job, if available.
    """
    # To default debug.log
    cdr.logwrite("%s: %s" % (SCRIPT, msg))

    # To job log
    if job:
        job.log("Fatal error: %s" % msg)

    # Abort
    sys.exit(1)


class FilterTransform:
    """
    Implements doc ID selection and transformation.  One of these is
    instantiated for each of the five selections
    """
    def __init__(self, reason, selQry):
        """
        Store the data needed for one category of documents that will
        not be transferred to CTGov.
        """
        self.reason = reason
        self.selQry = selQry

        # Access to the ModifyDocs job logger
        self.job = None

    def getDocIds(self):
        """
        Return CDR IDs for the docs.
        """
        # Get doc ids
        try:
            # This took up to 10 minutes when I ran it in QueryAnalyzer.
            # I think it was a fluke due to other stuff on the machine,
            #   but I'm setting a high timout just in case.
            conn = cdrdb.connect('cdr')
            cursor = conn.cursor()
            cursor.execute(self.selQry, timeout=1200)
            rows = cursor.fetchall()
            cursor.close()
        except cdrdb.Error, info:
            fatal("Unable to select documents\n%s" % info, self.job)

        # Log and return the row count
        self.job.log("Retrieved %d doc IDs for reason: %s" %
                     (len(rows), self.reason))
        return [row[0] for row in rows]


    def run(self, docObj):
        """
        Transform one doc.

        Pass:
            Document object for doc to transform.
        """
        # Date we start the transformation
        currentDate = time.strftime("%Y-%m-%d")

        # Transform the InScopeProtocol doc
        parms = (("currentDate", currentDate),
                 ("reasonComment", self.reason))

        response = cdr.filterDoc('guest', TRANSFORM, doc=docObj.xml,
                                 parm=parms, inline=True)

        # String response would be error message
        if type(response) in (type(""), type(u"")):
            self.job.log("Error msg from filterDoc: %s" % response)
            raise Exception("Failure in filterDoc: %s" % response)

        # Return transformed XML
        return response[0]


####################################
#               Main
####################################
if __name__ == "__main__":

    # DEBUG
    cdr.logwrite("Request4721.py: starting")

    # Args
    if len(sys.argv) < 4:
        # DEBUG
        cdr.logwrite("Request4721.py: wrong number of arguments (%s)" %
                      str(sys.argv))
        print("usage: Request4721.py uid pw {test|run}")
        sys.exit(1)
    uid = sys.argv[1]
    pw  = sys.argv[2]

    testMode = None
    if sys.argv[3] == 'test':
        testMode = True
    elif sys.argv[3] == 'run':
        testMode = False
    else:
        fatal('Must specify "test" or "run"')
        sys.exit(1)

    # Store all the FilterTransform objects here
    filtTrans = []

    # Filter to modify the document, one filter for all transforms
    TRANSFORM = """<xsl:transform version = '1.0'
          xmlns:xsl = 'http://www.w3.org/1999/XSL/Transform'
          xmlns:cdr = 'cips.nci.nih.gov/cdr'>

 <xsl:output method = 'xml'/>

 <!--
  Assumptions guaranteed by SQL selection critieria:
    There is no existing TransferContactLog
 -->
 <!-- Date global was initiated -->
 <xsl:param name = 'currentDate'/>

 <!-- Comment to add explaining the reason why transfer is not required -->
 <xsl:param name = 'reasonComment'/>

 <!-- Default copies input to output -->
 <xsl:template match = '@*|node()|comment()|processing-instruction()'>
  <xsl:copy>
   <xsl:apply-templates select = '@*|node()|comment()|text()|
                                    processing-instruction()'/>
  </xsl:copy>
 </xsl:template>

 <xsl:template match = 'ProtocolIDs'>
   <!-- Copy the IDs.  They are required and must exist -->
   <xsl:copy-of select = '.'/>

   <!-- Create contact log with our fields -->
   <xsl:element name = 'CTGovOwnershipTransferContactLog'>
     <xsl:element name = 'CTGovOwnershipTransferContactResponse'>
       <xsl:text>Transfer not required</xsl:text>
     </xsl:element>
     <xsl:element name = 'Date'>
       <xsl:value-of select = '$currentDate'/>
     </xsl:element>
     <xsl:element name = 'Comment'>
       <xsl:value-of select = '$reasonComment'/>
     </xsl:element>
   </xsl:element>
 </xsl:template>
</xsl:transform>
"""

    # Create the five FilterTransforms that we'll use
    filtTrans.append(FilterTransform("Never registered in CTGov", """
-- Query1: InScopeProtocols with no NCTID.
-- "Never registered in CTGOV".
-- Excludes docs not in NCTID because they haven't progressed that far
SELECT DISTINCT d.id
  FROM document d
  JOIN doc_type t
    ON d.doc_type = t.id
   AND t.name = 'InScopeProtocol'
  JOIN query_term q
    ON d.id = q.doc_id
 WHERE d.id NOT IN (
        SELECT doc_id
          FROM query_term
         WHERE path = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
           AND value = 'ClinicalTrials.gov ID'
	)
   AND d.id NOT IN (
        SELECT doc_id
          FROM query_term
         WHERE path IN (
           '/InScopeProtocol/CTGovOwnershipTransferContactLog/CTGovOwnershipTransferContactResponse',
           '/InScopeProtocol/CTGovOwnershipTransferInfo/CTGovOwnerOrganization'
         )
    )
   AND d.id NOT IN (
        SELECT doc_id
          FROM query_term
         WHERE path IN (
          '/InScopeProtocol/ProtocolProcessingDetails/ProcessingStatuses/ProcessingStatusInfo/ProcessingStatus',
          '/InScopeProtocol/ProtocolProcessingDetails/ProcessingStatus'
           )
           AND value in (
            'Pending',
            'Hold',
            'Abstract in review',
            'Merged',
            'Needs administrative information'
           )
    )
   AND d.id NOT IN (
        SELECT doc_id
          FROM query_term
         WHERE path =
          '/InScopeProtocol/ProtocolProcessingDetails/MissingRequiredInformation/MissingInformation'
    )
 ORDER BY d.id
"""))

    filtTrans.append(FilterTransform("Blocked From CTGov",
"""
-- Query2: InScopeProtocols with an NCTID but are blocked from CTGOV.
-- "Blocked from CTGOV".
SELECT DISTINCT qIdType.doc_id
  FROM query_term qIdType
  JOIN query_term qBlocked
    ON qIdType.doc_id = qBlocked.doc_id
 WHERE qIdType.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
   AND qIdType.value = 'ClinicalTrials.gov ID'
   AND qBlocked.path = '/InScopeProtocol/BlockedFromCTGov'
   AND qIdType.doc_id NOT IN (
        SELECT doc_id
          FROM query_term
         WHERE path IN (
           '/InScopeProtocol/CTGovOwnershipTransferContactLog/CTGovOwnershipTransferContactResponse',
           '/InScopeProtocol/CTGovOwnershipTransferInfo/CTGovOwnerOrganization'
         )
    )
 ORDER BY qIdType.doc_id
"""))

    filtTrans.append(FilterTransform("Completed prior to Sept 27, 2007",
"""
-- Query3: InScopeProtocols with an NCTID and are Completed before 2007-09-27.
-- "Completed prior to Sept 27, 2007".
SELECT DISTINCT qCurStat.doc_id
  FROM query_term qCurStat
  JOIN query_term qIdType
    ON qCurStat.doc_id = qIdType.doc_id
   AND qIdType.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
   AND qIdType.value = 'ClinicalTrials.gov ID'
  JOIN query_term qLeadOrg
    ON qCurStat.doc_id = qLeadOrg.doc_id
   AND qLeadOrg.path =
    '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg/LeadOrgRole'
   AND qLeadOrg.value = 'Primary'
  JOIN query_term qOrgStat
    ON qCurStat.doc_id = qOrgStat.doc_id
   AND qOrgStat.path =
    '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg/LeadOrgProtocolStatuses/CurrentOrgStatus/StatusName'
   AND qOrgStat.value = 'Completed'
   AND LEFT(qOrgStat.node_loc, 8) = LEFT(qLeadOrg.node_loc, 8)
  JOIN query_term qStatDt
    ON qCurStat.doc_id = qStatDt.doc_id
   AND qStatDt.path =
    '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg/LeadOrgProtocolStatuses/CurrentOrgStatus/StatusDate'
   AND qStatDt.value < '2007-09-27'
   AND LEFT(qStatDt.node_loc, 8) = LEFT(qLeadOrg.node_loc, 8)
 WHERE qCurStat.path =
    '/InScopeProtocol/ProtocolAdminInfo/CurrentProtocolStatus'
   AND qCurStat.value = 'Completed'
   AND qCurStat.doc_id NOT IN (
        SELECT doc_id
          FROM query_term
         WHERE path IN (
           '/InScopeProtocol/CTGovOwnershipTransferContactLog/CTGovOwnershipTransferContactResponse',
           '/InScopeProtocol/CTGovOwnershipTransferInfo/CTGovOwnerOrganization'
         )
    )
 ORDER BY qCurStat.doc_id
"""))

    filtTrans.append(FilterTransform("Withdrawn from PDQ",
"""
-- Query4: InScopeProtocols with NCTID that were withdrawn from PDQ.
-- "Withdrawn from PDQ".
SELECT DISTINCT qCurStat.doc_id
  FROM query_term qCurStat
  JOIN query_term qIdType
    ON qCurStat.doc_id = qIdType.doc_id
   AND qIdType.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
   AND qIdType.value = 'ClinicalTrials.gov ID'
  WHERE qCurStat.path =
    '/InScopeProtocol/ProtocolAdminInfo/CurrentProtocolStatus'
   AND qCurStat.value = 'Withdrawn from PDQ'
   AND qCurStat.doc_id NOT IN (
        SELECT doc_id
          FROM query_term
         WHERE path IN (
           '/InScopeProtocol/CTGovOwnershipTransferContactLog/CTGovOwnershipTransferContactResponse',
           '/InScopeProtocol/CTGovOwnershipTransferInfo/CTGovOwnerOrganization'
         )
    )
 ORDER BY qCurStat.doc_id
"""))

    filtTrans.append(FilterTransform("Withdrawn prior to Sept 27, 2007",
"""
-- Query5: InScopeProtocols withdrawn before 2007-09-27.
-- Identical to Query3 except both status="Withdrawn" instead of "Completed"
-- "Withdrawn prior to Sept 27, 2007".
SELECT DISTINCT qCurStat.doc_id
  FROM query_term qCurStat
  JOIN query_term qIdType
    ON qCurStat.doc_id = qIdType.doc_id
   AND qIdType.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
   AND qIdType.value = 'ClinicalTrials.gov ID'
  JOIN query_term qLeadOrg
    ON qCurStat.doc_id = qLeadOrg.doc_id
   AND qLeadOrg.path =
    '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg/LeadOrgRole'
   AND qLeadOrg.value = 'Primary'
  JOIN query_term qOrgStat
    ON qCurStat.doc_id = qOrgStat.doc_id
   AND qOrgStat.path =
    '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg/LeadOrgProtocolStatuses/CurrentOrgStatus/StatusName'
   AND qOrgStat.value = 'Withdrawn'
   AND LEFT(qOrgStat.node_loc, 8) = LEFT(qLeadOrg.node_loc, 8)
  JOIN query_term qStatDt
    ON qCurStat.doc_id = qStatDt.doc_id
   AND qStatDt.path =
    '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg/LeadOrgProtocolStatuses/CurrentOrgStatus/StatusDate'
   AND qStatDt.value < '2007-09-27'
   AND LEFT(qStatDt.node_loc, 8) = LEFT(qLeadOrg.node_loc, 8)
 WHERE qCurStat.path =
    '/InScopeProtocol/ProtocolAdminInfo/CurrentProtocolStatus'
   AND qCurStat.value = 'Withdrawn'
   AND qCurStat.doc_id NOT IN (
        SELECT doc_id
          FROM query_term
         WHERE path IN (
           '/InScopeProtocol/CTGovOwnershipTransferContactLog/CTGovOwnershipTransferContactResponse',
           '/InScopeProtocol/CTGovOwnershipTransferInfo/CTGovOwnerOrganization'
         )
    )
 ORDER BY qCurStat.doc_id
"""))

    ####################################
    # Run all the global changes
    ####################################

    # DEBUG
    # testMode = True     # No database update

    for glbl in filtTrans:
        # Instantiate a job for this selection criteria
        job = ModifyDocs.Job(uid, pw, glbl, glbl,
          'Global change to add "Transfer not required" statements to '
          'InScopeProtocols that will never go to CTGov.  Request 4721.\n'
          'Running section with reason: %s' % glbl.reason,
          validate=True, testMode=testMode)

        # Turn off saving of last and last publishable versions
        job.setTransformVER(False)

        # Add a reference to the job into the FilterTransform for
        # access to the job logger while running
        glbl.job = job

        # DEBUG
        # job.setMaxDocs(50)

        # Global change
        job.run()

        # Ensure log file cleanup
        job.__del__()

    # DEBUG
    cdr.logwrite("Request4721.py: completed")
