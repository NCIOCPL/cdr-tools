#----------------------------------------------------------------------
# Global change to remove the SummarySection containing the purpose
# of the Summary.  It will be replaced by boilerplate added by the
# vendor filters at publishing time.
#
# BZIssue::4838
#----------------------------------------------------------------------
import sys, cdr, cdrdb, ModifyDocs

class FilterTransform:
    """
    Defines functions to select doc IDs and transform them.
    """
    def __init__(self):
        # Access to ModifyDocs job for logging
        self.job = None

    def getDocIds(self):
        """
        Select and return CDR IDs for docs to transform
        """
        try:
            conn = cdrdb.connect()
            cursor = conn.cursor()
            cursor.execute("""
      SELECT d.id
        FROM document d
        JOIN doc_type t
          ON d.doc_type = t.id
        JOIN query_term q
          ON d.id = q.doc_id
       WHERE t.name = 'Summary'
         AND q.path = '/Summary/SummaryMetadata/SummaryAudience'
         AND q.value = 'Health professionals'
""")
            rows = cursor.fetchall()
        except cdrdb.Error, info:
            self.job.log("Error selecting doc IDs: %s" % info)
            raise Exception("Failure selecting IDs: %s" % info)

        # DEBUG one English and one Spanish
        # return[62675, 256621]

        return [row[0] for row in rows]


    def run(self, docObj):
        """
        Transform one doc.

        Pass:
            Object in cdr.Doc format.
        """
        xsl = """<?xml version='1.0' encoding='UTF-8'?>
<xsl:transform  version = '1.0'
                xmlns:xsl = 'http://www.w3.org/1999/XSL/Transform'
                xmlns:cdr = 'cips.nci.nih.gov/cdr'>
 <xsl:output    method = 'xml'/>

 <!-- ==================================================================
 Copy almost everything straight through.
 ======================================================================= -->
 <xsl:template match='@*|node()|text()|comment()|processing-instruction()'>
   <xsl:copy>
       <xsl:apply-templates select='@*|node()|text()|comment()|
                                    processing-instruction()'/>
   </xsl:copy>
 </xsl:template>

 <!-- Check to see if SummarySection is the one we want -->
 <xsl:template match = '/Summary/SummarySection'>
   <xsl:if test = 'not(./Title = "Purpose of This PDQ Summary") and
                   not(./Title = "Prop\xC3\xB3sito de este sumario del PDQ")'>
     <!-- This one is kept, copy it to output -->
     <xsl:copy-of select = '.'/>
   </xsl:if>
   <!-- Otherwise it's the one to block.  Do nothing with it -->
 </xsl:template>

</xsl:transform>
"""

        # Filter the doc
        response = cdr.filterDoc('guest', xsl, doc=docObj.xml, inline=True)

        # String response is an error
        if type(response) in (type(""), type(u"")):
            self.job.log("Error filtering docId: %s: %s" %
                          (docObj.id, response))
            raise Exception("Failure in filterDoc: %s" % response)

        # Got back a filtered doc
        return response[0]


if __name__ == '__main__':
    # Args
    if len(sys.argv) < 4:
        print("usage: Request4838.py uid pw {test|run}")
        sys.exit(1)
    uid   = sys.argv[1]
    pw    = sys.argv[2]

    testMode = None
    print(sys.argv[3].lower())
    if sys.argv[3].lower() == 'test':
        testMode = True
    elif sys.argv[3].lower() == 'run':
        testMode = False
    else:
        sys.stderr.write('Must specify "test" or "run"')
        sys.exit(1)

    # Instantiate our object, loading the spreadsheet
    filtTrans = FilterTransform()

    # Debug
    # testMode = 'test'

    # Instantiate ModifyDocs job
    job = ModifyDocs.Job(uid, pw, filtTrans, filtTrans,
      'Global update to remove "Purpose" SummarySection from English and '
      'Spanish Summaries.  Request 4838.', validate=True,
      testMode=testMode)

    # Install access to job in FilterTransform for logging
    filtTrans.job = job

    # Debug
    # job.setMaxDocs(20)

    # Global change
    job.run()
