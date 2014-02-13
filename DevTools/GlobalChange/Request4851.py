#----------------------------------------------------------------------
# $Id$
#
# Global change to add "Foreign Trial - No Domestic Site" to InScopeProtocols
# for which it is known that no transfer to CTGov will be required because
# the trials are not run in the U.S.
#
# BZIssue::4851
#----------------------------------------------------------------------
import sys, time, cdr, cdrdb, ModifyDocs
import lxml.etree as ltree

# Name of the program for logging
SCRIPT = "Request4851.py"

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
    def __init__(self):
        """
        Produce a searchable set of all U.S. Organizations.  It will
        be used to check every Organization site in each protocol.  If
        any site is for a U.S. organization, change will be aborted
        for that protocol.
        """
        # For access to the ModifyDocs job logger
        self.job = None

        # Date we start the transformation
        self.currentDate = time.strftime("%Y-%m-%d")

        # Get the Org ID list
        try:
            conn = cdrdb.connect()
            cursor = conn.cursor()
            cursor.execute("""
        SELECT DISTINCT doc_id
          FROM query_term
         WHERE path = '/Organization/OrganizationLocations' +
                      '/OrganizationLocation/Location/PostalAddress/Country'
           AND value = 'U.S.A'
            """, timeout=60)
            rows = cursor.fetchall()
        except cdrdb.Error, info:
            fatal("Error fetching Org country info: %s" % info)

        # Create a set with one entry for every Org with a U.S. location.
        # We already know that there are no Orgs with both U.S. and
        #   non-U.S. locations.
        self.USOrgs = set([row[0] for row in rows])


    def getDocIds(self):
        """
        Return CDR IDs for the docs.

        These originate in a spreadsheet prepared by Kim Eckley.  They
        have been extracted into a list of sorted ID's, one per line,
        in a text file.

        We read the text file into an in memory list and return that to
        the ModifyDocs job.
        """
        fname = "GlobalForeignTrialIDs.txt"
        # Get doc ids
        try:
            fp = open(fname, "r")
            docIdLines = fp.read()
            fp.close()
        except IOError, info:
            fatal("Error reading file %s: %s" % (fname, info))

        # Convert the lines of text to a list of numbers
        docIdsTxt = docIdLines.split()
        docIds = []
        for docId in docIdsTxt:
            docIds.append(int(docId))

        return docIds


    def run(self, docObj):
        """
        Check the contents of one doc.  If it is okay to transform,
        transform and return it.

        Otherwise, just return the original, unmodified doc.  The ModifyDocs
        module will see that it has not changed and so not save it.

        Pass:
            Document object for doc to transform.
        """
        # Parse the doc to look for anything that shouldn't be there
        try:
            tree = ltree.fromstring(docObj.xml)
        except Exception, info:
            # Skip this doc
            self.job.log("Unable to parse doc ID=%s: %s" % (docObj.id, info))
            return docObj.xml

        # Contact info already present?
        # if tree.findall('CTGovOwnershipTransferContactResponse'):
        if tree.findall('CTGovOwnershipTransferContactLog'
                        '/CTGovOwnershipTransferContactResponse'):
            self.job.log("Skipping doc ID=%s: Already has ContactResponse" %
                          docObj.id)
            return docObj.xml
        if tree.findall('CTGovOwnershipTransferInfo/CTGovOwnerOrganization'):
            self.job.log("Skipping doc ID=%s: Already has TranferInfo" %
                          docObj.id)
            return docObj.xml

        # Is there a U.S. site?
        orgSites = tree.xpath(
                    './ProtocolAdminInfo/ProtocolLeadOrg'
                    '/ProtocolSites/OrgSite/OrgSiteID/@cdr:ref',
                    namespaces={"cdr": "cips.nci.nih.gov/cdr"})
        if orgSites:
            for siteId in orgSites:
                siteIdNum = cdr.exNormalize(siteId)[1]
                if siteIdNum in self.USOrgs:
                    self.job.log("Skipping doc ID=%s: OrgSiteID=%s is in U.S."
                                  % (docObj.id, siteId))
                    return docObj.xml

        # If we got this far, transform the InScopeProtocol doc
        parms = (("currentDate", self.currentDate),)

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
       <xsl:text>Foreign Trial - No Domestic Site</xsl:text>
     </xsl:element>
     <xsl:element name = 'Date'>
       <xsl:value-of select = '$currentDate'/>
     </xsl:element>
   </xsl:element>
 </xsl:template>
</xsl:transform>
"""

    ####################################
    # Run all the global changes
    ####################################

    # DEBUG
    # testMode = True     # No database update

    # Instantiate an object to do the work
    ft = FilterTransform()

    # Instantiate a job for this selection criteria
    job = ModifyDocs.Job(uid, pw, ft, ft,
      'Global change to add "Foreign Trial - No Domestic Site" '
      'statements to InScopeProtocols that will not go to CTGov for '
      'the stated reason.  Request 4851.\n',
      validate=True, testMode=testMode)

    # Turn off saving of last and last publishable versions
    job.setTransformVER(False)

    # Add a reference to the job into the FilterTransform for
    # access to the job logger while running
    ft.job = job

    # DEBUG
    # job.setMaxDocs(2)

    # Global change
    job.run()

    # Ensure log file cleanup
    # job.__del__()

    # DEBUG
    cdr.logwrite("Request4851.py: completed")
