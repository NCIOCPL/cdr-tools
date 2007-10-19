#----------------------------------------------------------------------
# One off change to coalesce six different SemanticType values into
# one.  Only the cdr:ref attributes to the semantic type term
# documents need to be changed.
#
# SemanticTypes to replace:
#    539747 - Behavioral/psychological/informational intervention/procedure
#    256160 - Cancer therapy modality
#    256162 - Diagnostic test/procedure
#    256163 - Preventative intervention/procedure
#    482272 - Screening intervention/procedure
#    256161 - Supportive care modality
#    256159 - Therapeutic intervention or procedure
#
# New type that replaces them:
#    256087 - Intervention or procedure
#
# $Id: Request3680.py,v 1.1 2007-10-19 04:15:44 ameyer Exp $
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdr, cdrdb, ModifyDocs, sys

#----------------------------------------------------------------------
# Filter class for ModifyDocs.
#----------------------------------------------------------------------
class Filter:
    def getDocIds(self):
        """
        Selects all doc ids from query_term_pub that have one of the
        six SemanticTypes of interest.

        A check of Bach showed that all entries in the query_term
        table with one of the six types also existed in the query_term_pub
        table with one of the six types.  However there were three
        entries in query_term_pub that were not in query_term.

        I checked them manually.  All had been edited to refer to the
        new semantic type.  Presumably, no publishable version of the
        change had yet been saved.  Therefore I do the selection in
        query_term_pub in order to be sure to change everything.
        """
        conn = cdrdb.connect('CdrGuest')
        cursor = conn.cursor()

        cursor.execute("""\
          SELECT doc_id
            FROM query_term_pub
           WHERE path = '/Term/SemanticType/@cdr:ref'
             AND int_val IN (539747,256160,256162,256163,482272,256161,256159)
        ORDER BY doc_id""")

        # Return the first element of each row in a sequence instead
        # of a sequence of sequences
        return [row[0] for row in cursor.fetchall()]

#----------------------------------------------------------------------
# Transformation run against each selected doc by ModifyDocs
#----------------------------------------------------------------------
class Transform:
    def run(self, docObj):

        xsl = """<?xml version='1.0' encoding='UTF-8'?>

<xsl:transform  version = '1.0'
                xmlns:xsl = 'http://www.w3.org/1999/XSL/Transform'
                xmlns:cdr = 'cips.nci.nih.gov/cdr'>
 <xsl:output    method = 'xml'/>

 <!-- ==================================================================
 Copy almost everything straight through.
 ======================================================================= -->
 <xsl:template             match = '@*|node()|comment()|
                                    processing-instruction()'>
  <xsl:copy>
   <xsl:apply-templates   select = '@*|node()|comment()|text()|
                                    processing-instruction()'/>
  </xsl:copy>
 </xsl:template>

 <!-- Node of interest -->
 <xsl:template             match = '/Term/SemanticType'>

   <!-- Create new, empty element -->
   <xsl:copy>
     <!-- Copy any PdqKey attribute -->
     <xsl:if                test = '@PdqKey'>
       <xsl:copy-of select='@PdqKey'/>
     </xsl:if>

     <!-- Replace cdr:ref with new one -->
     <xsl:attribute name='cdr:ref'>CDR00000256087</xsl:attribute>

     <!-- Denormalized text isn't required, but let's do it anyway -->
     <xsl:text>Intervention/procedure</xsl:text>
   </xsl:copy>
 </xsl:template>
</xsl:transform>
"""
        response = cdr.filterDoc('guest', xsl, doc=docObj.xml, inline=1)
        if type(response) in (type(""), type(u"")):
            raise Exception("Failure in filterDoc: %s" % response)
        return response[0]

# Note: Testing for main enables pychecker import without running
if __name__ == '__main__':
    # Args
    if len(sys.argv) < 3:
        print("usage: Request3680.py uid pw {run}")
        sys.exit(1)

    # To run with real database update, pass userid, pw, 'run' on cmd line
    testMode = True
    if len(sys.argv) > 3:
        if sys.argv[3] == 'run':
            testMode = False

    # Instantiate ModifyDocs job
    job = ModifyDocs.Job(sys.argv[1], sys.argv[2], Filter(), Transform(),
      "Global replace 6 different SemanticTypes with 1 - Request 3680.",
      testMode=testMode)

    # Turn off all modifications except for Current Working Document
    job.setTransformANY(False)
    job.setTransformPUB(False)
    # job.setMaxDocs(2)

    # Global change
    job.run()
