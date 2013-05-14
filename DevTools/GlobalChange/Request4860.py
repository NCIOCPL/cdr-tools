#----------------------------------------------------------------------
# Global change to mark Terms with the semantic type "Drug/agent category"
# as obsolete, and block them.
#
# BZIssue::4860
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
        CDR0000256164 is the known id for the Term defining the
        SemanticType "Drug/agent category"
        """
        try:
            conn = cdrdb.connect()
            cursor = conn.cursor()
            cursor.execute("""
        SELECT doc_id
          FROM query_term
         WHERE path = '/Term/SemanticType/@cdr:ref'
           AND value = 'CDR0000256164'
         ORDER BY doc_id
""")
            rows = cursor.fetchall()
        except cdrdb.Error, info:
            self.job.log("Error selecting doc IDs: %s" % info)
            raise Exception("Failure selecting IDs: %s" % info)

        return [row[0] for row in rows]


    def run(self, docObj):
        """
        Transform one doc.

        Pass:
            Object in cdr.Doc format.
        """
        xsl = """<?xml version='1.0' encoding='UTF-8'?>

<xsl:transform                version = '1.0'
                            xmlns:xsl = 'http://www.w3.org/1999/XSL/Transform'
                            xmlns:cdr = 'cips.nci.nih.gov/cdr'>

 <xsl:output                   method = 'xml'/>

 <!--
 =======================================================================
 Copy almost everything straight through.
 ======================================================================= -->
 <xsl:template                  match = '@*|node()|comment()|
                                         processing-instruction()'>
   <xsl:copy>
     <xsl:apply-templates      select = '@*|node()|comment()|text()|
                                         processing-instruction()'/>
   </xsl:copy>
 </xsl:template>

 <xsl:template                  match = '/Term/TermType'>

   <TermType>
     <!-- Copy any existing TermTypeNames, or whatever is there -->
     <xsl:for-each             select = '@*|node()|comment()|text()|
                                         processing-instruction()'>
       <xsl:copy-of select = "."/>
     </xsl:for-each>

     <!-- Add a term type name of "Obsolete term" -->
     <xsl:element                  name = 'TermTypeName'>
       <xsl:text>Obsolete term</xsl:text>
     </xsl:element>
   </TermType>
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
        print("usage: Request4860.py uid pw test|run {maxdocs}")
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
    maxdocs = None
    if len(sys.argv) == 5:
        maxdocs = int(sys.argv[4])

    # Instantiate our object, loading the spreadsheet
    filtTrans = FilterTransform()

    # Debug
    # testMode = 'test'

    # Instantiate ModifyDocs job
    job = ModifyDocs.Job(uid, pw, filtTrans, filtTrans,
      'Global update to mark "Drug/agent category" Terms as obsolete '
      'and block them.  Request 4860.', validate=True,
      testMode=testMode)

    # Save only the CWD, no versions, except old CWD becomes new last version
    #   if it had never before been saved.
    job.setTransformVER(False)

    # If user requests limit on max docs
    if maxdocs is not None:
        job.setMaxDocs(maxdocs)

    # Cause all docs to be blocked while saving them
    job.setActiveStatus('I')

    # Install access to job in FilterTransform for logging
    filtTrans.job = job

    # Global change
    job.run()
