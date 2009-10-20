#----------------------------------------------------------------------
# Global change to replace references to InScopeProtocol documents
# that have been replaced by CTGovProtocol versions.
#
# Satisfies Bugzilla request 4632.  See comments in Bugzilla for details.
#
# $Id$
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2009/09/09 03:54:13  ameyer
# Initial version.
#
#
#----------------------------------------------------------------------
import sys, datetime, cdr, cdrdb, ModifyDocs

# Name of the program for logging
SCRIPT = "Request4632.py"

# Collect all the data we need and return a list of doc IDs to be changed
# In Python, we have to store a procedure first, or else execute these
#   as a series of statements
SELECT_ALL_QUERIES = ("""
-- Delete any tables hanging around
IF OBJECT_ID('inscope2ctgov_map', 'U') IS NOT NULL
  DROP TABLE inscope2ctgov_map
""",
"""
IF OBJECT_ID('inscope2ctgov_refs', 'U') IS NOT NULL
  DROP TABLE inscope2ctgov_refs
""",
"""
-- Create a table to map InScopeProtocol CDR IDs to CTGovProtocol CDR IDs.
CREATE TABLE inscope2ctgov_map (
  inscope_id INT NULL,
  ctgov_id   INT NULL,
  nct_id     VARCHAR(12) NULL
)
""",
"""
-- Create a table to link source documents that have an InScope CDR ID
--   to the table that maps them to CTGov CDR IDs
CREATE TABLE inscope2ctgov_refs (
  src_id INT,
  trg_id INT
)
""",
"""
-- Find inactive InScope doc CDR IDs with an associated nct_id
INSERT inscope2ctgov_map (inscope_id, nct_id)
  SELECT q.doc_id, q.value
    FROM query_term q
    JOIN query_term q2
      ON q.doc_id = q2.doc_id
     AND LEFT(q.node_loc, 8) = LEFT(q2.node_loc, 8)
    JOIN all_docs d
      ON q.doc_id = d.id
   WHERE q.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDString'
     AND q2.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
     AND q2.value = 'ClinicalTrials.gov ID'
     AND d.active_status = 'I'
""",
"""
-- If there's a corresponding active CTGov doc, add it's CDR ID
UPDATE inscope2ctgov_map
   SET inscope2ctgov_map.ctgov_id = query_term_pub.doc_id
  FROM query_term_pub
 WHERE inscope2ctgov_map.nct_id = query_term_pub.value
   AND query_term_pub.path = '/CTGovProtocol/IDInfo/NCTID'
""",
"""
-- Get rid of any that don't have a current CTGov doc
-- These might be withdrawn by CTGov or whatever, but we can't link them
DELETE inscope2ctgov_map
 WHERE ctgov_id IS NULL
""",
"""
-- Populate the table of documents that reference the InScopeProtocols
--   in the mapping table.
-- Note that one document may reference more than one protocol
INSERT inscope2ctgov_refs (src_id, trg_id)
SELECT q.doc_id, m.inscope_id
  FROM query_term_pub q
  JOIN all_docs d
    ON q.doc_id = d.id
  JOIN doc_type t
    ON d.doc_type = t.id
  JOIN inscope2ctgov_map m
    ON q.int_val = m.inscope_id
 WHERE (path LIKE '%/@cdr:href' OR path LIKE '%/@cdr:ref')
   AND t.name <> 'Mailer'
 -- Uncomment the following to skip docs that are themselves being replaced
 -- AND q.doc_id NOT IN (SELECT m.inscope_id FROM inscope2ctgov_map g)
 -- OR uncomment the following to skip all inactive docs, including above
 -- AND t.active_status = 'A'
""",
"""
-- Find docs to change for ModifyDocs module
-- This is the one that returns rows to the global change program
SELECT DISTINCT src_id
  FROM inscope2ctgov_refs
 ORDER BY src_id
""")

# Run once for each doc to change
ONE_DOC_QRY = """
-- Select all rows of InScope + matching CTGov CDR IDs for one source doc
SELECT r.src_id, m.inscope_id, m.ctgov_id
  FROM inscope2ctgov_map m
  JOIN inscope2ctgov_refs r
    ON r.trg_id = m.inscope_id
 WHERE r.src_id = %d
 GROUP BY r.src_id, m.inscope_id, m.ctgov_id
 ORDER BY r.src_id
"""

# Tranform for replacing one cdr:ref or href with another
TRANSFORM = """<xsl:transform version = '1.0'
               xmlns:xsl = 'http://www.w3.org/1999/XSL/Transform'
               xmlns:cdr = 'cips.nci.nih.gov/cdr'>

 <xsl:output method = 'xml'/>

 <!-- $inID   = CDR ID already in the record.
      $outID  = CDR ID to replace it in output record. -->
 <xsl:param name='inID'/>
 <xsl:param name='outID'/>

 <!--
 =======================================================================
 Copy almost everything straight through.
 ======================================================================= -->
 <xsl:template match = '@*|node()|comment()|
                                    processing-instruction()'>
  <xsl:copy>
   <xsl:apply-templates select = '@*|node()|comment()|text()|
                                    processing-instruction()'/>
  </xsl:copy>
 </xsl:template>

 <!-- Convert ref and href attributes -->
 <xsl:template match = "//@cdr:href">
   <!-- DEBUGGING
    <xsl:message
      terminate='no'>=== $inID=<xsl:value-of select='$inID'/></xsl:message>
    <xsl:message
      terminate='no'>=== $outID=<xsl:value-of select='$outID'/></xsl:message>
    <xsl:message
      terminate='no'>.=<xsl:value-of select='.'/></xsl:message>
   -->
   <xsl:choose>
     <xsl:when test = "substring(., 1, 13) = $inID">
       <xsl:attribute
            name = "cdr:href"><xsl:value-of select="$outID"/></xsl:attribute>
     </xsl:when>
     <xsl:otherwise>
       <xsl:attribute
            name = "cdr:href"><xsl:value-of select="."/></xsl:attribute>
     </xsl:otherwise>
   </xsl:choose>
 </xsl:template>

 <xsl:template match = "//@cdr:ref">
   <xsl:choose>
     <xsl:when test = "substring(., 1, 13) = $inID">
       <xsl:attribute
            name = "cdr:ref"><xsl:value-of select="$outID"/></xsl:attribute>
     </xsl:when>
     <xsl:otherwise>
       <xsl:attribute
            name = "cdr:ref"><xsl:value-of select="."/></xsl:attribute>
     </xsl:otherwise>
   </xsl:choose>
 </xsl:template>
</xsl:transform>
"""

# Header for an HTML format report to be emailed to users
REPORT_HDR = """
<html>
 <head>
  <title>Report of InScope -> CTGov Reference Substitutions</title>
 </head>
 <body>
  <h3>Individual Document Transformations</h3>
  <table border='1'>
   <tr>
    <th>Changed Doc</th>
    <th>InScope ID</th>
    <th>CTGov ID</th>
   </tr>
"""

def fatal(msg):
    """
    Log an error and abort.
    """
    # To default debug.log
    cdr.logwrite("%s: %s" % (SCRIPT, msg))
    # Abort
    sys.exit(1)

class FilterTransform:

    def __init__(self):
        # We only need one connection, which we'll re-use as needed
        try:
            self.conn = cdrdb.connect('cdr')
            # Default is off, but this just confirms that
            self.conn.setAutoCommit(on=False)
        except cdrdb.Error, info:
            fatal ("Unable to connect to database: %s" % info)
        self.__conn = None

        # Prepare an HTML email report of what was done
        self.report = REPORT_HDR

        # Set of unique docs we processed
        self.inscopeIds = set()

        # Set of unique combinations we processed
        self.fullRows = set()

    def getDocIds(self):
        """
        Creates two tables in SQL Server that contain all the information
        needed for the global change.

        Then extracts the CDR IDs of the documents that will be changed,
        returning them as a list of docIds.
        """
        # Get the ids
        cursor = self.conn.cursor()
        for qry in SELECT_ALL_QUERIES:
            try:
                cursor.execute(qry, timeout=300)
            except cdrdb.Error, info:
                fatal("Unable to select documents:\nQry:\n%s\nError\n\%s" %
                      (qry, info))

        # Last query had the data we need
        rows = cursor.fetchall()
        cursor.close()

        return [row[0] for row in rows]


    def run(self, docObj):
        """
        Transform one doc.

        First looks up the doc in the table and retrieves all associated
        information.
        """
        # Get the document ID
        docId = cdr.exNormalize(docObj.id)[1]

        # XML into local variable that can be replaced
        docXml = docObj.xml

        # Retrieve list of linked ID / replacement link id from database
        try:
            # conn = cdrdb.connect()
            cursor = self.conn.cursor()
            cursor.execute(ONE_DOC_QRY % docId)
            rows = cursor.fetchall()
            cursor.close()
        except cdrdb.Error, info:
            fatal ("Unable to retrieve info for docID=%s: %s" %
                    (docId, info))

        # We have a list of one or more substitutions to make
        # Process each one in turn
        for row in rows:
            srcId, inscopeId, ctgovId = row

            # Sanity check
            if srcId != docId:
                fatal("srcId=%d docId=%d, can't happen" % (srcId, docId))

            # Normalize to CDR000... form
            inscopeIdStr = cdr.normalize(inscopeId)
            ctgovIdStr   = cdr.normalize(ctgovId)

            # Filter the doc with these parameters
            # Output becomes input to next parms, if any
            # Filter works on any doctype
            parms = (("inID", inscopeIdStr), ("outID", ctgovIdStr))
            response = cdr.filterDoc('guest', TRANSFORM,
                                     doc=docXml, parm=parms, inline=True)

            # String response would be error message
            if type(response) in (type(""), type(u"")):
                # Must have gotten an error message
                raise Exception("Failure in filterDoc: %s" % response)

            # Output will be filtered again if there are more rows of parms
            docXml = response[0]

            # Add to report
            if str(row) not in self.fullRows:
                self.fullRows.add(str(row))
                self.report += \
                  "   <tr><td>%d</td><td>%d</td><td>%d</td></tr>\n" % \
                  (srcId, inscopeId, ctgovId)
            self.inscopeIds.add(inscopeId)

        # Return final version after all substitutions are complete
        return docXml

    def sendReport(self, jobObj):
        """
        Complete a report and send it.

        Pass:
            jobObj - Job object for access to statistics.
        """
        self.report += """
  </table>
  <p><h3>Summary</h3>
  <table>
   <tr><td align='right'>Documents processed: </td><td>%d</td></tr>
   <tr><td align='right'>Documents saved: </td><td>%d</td></tr>
   <tr><td align='right'>Versions processed: </td><td>%d</td></tr>
   <tr><td align='right'>Unique InScope->CTGov mappings: </td><td>%d</td></tr>
  </table>
 </body>
</html>
""" % (jobObj.getCountDocsProcessed(), jobObj.getCountDocsSaved(),
       jobObj.getCountVersionsSaved(), len(self.inscopeIds))

        notCheckedOut = jobObj.getNotCheckedOut(markup=True)
        if notCheckedOut:
            self.report += "\n<h3>Documents that could not be changed</h3>\n"
            self.report += notCheckedOut

        sender = "cdr@%s" % cdr.getHostName()[1]
        recips = cdr.getEmailList("CTGov Link Fix Notification")
        subject= "Global change report (%s): %s" % \
                  (datetime.date.today(),
                   "InScope->CTGov reference substitutions")

        cdr.sendMail(sender, recips, subject, self.report, "html")

if __name__ == '__main__':
    # DEBUG
    cdr.logwrite("Request4632.py: starting")

    # Args
    if len(sys.argv) < 4:
        # DEBUG
        cdr.logwrite("Request4632.py: wrong arguments (%s)" % str(sys.argv))
        print("usage: Request4632.py uid pw {test|run}")
        sys.exit(1)
    uid   = sys.argv[1]
    pw    = sys.argv[2]

    testMode = None
    if sys.argv[3] == 'test':
        testMode = True
    elif sys.argv[3] == 'run':
        testMode = False
    else:
        fatal('Must specify "test" or "run"')
        sys.exit(1)

    # DEBUG
    # testMode = True

    # Instantiate our object
    filtTrans = FilterTransform()

    # Instantiate ModifyDocs job
    job = ModifyDocs.Job(uid, pw, filtTrans, filtTrans,
      "Global change of references from former InScopeProtocol to current" +
      "CTGovProtocol.  Request 4632.",
      testMode=testMode)

    # DEBUG
    # job.setMaxDocs(5)

    # Global change
    job.run()

    # DEBUG
    # To save or delete tables uncomment the commit or rollback
    # Saving is unnecessary but aids debugging
    filtTrans.conn.commit()
    # filtTrans.conn.rollback()

    # Complete and email a report
    filtTrans.sendReport(job)

    # DEBUG
    cdr.logwrite("Request4632.py: completed")
