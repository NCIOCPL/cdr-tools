#----------------------------------------------------------------------
# One off change to coalesce seven different SemanticType values into
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
# $Id: Request3680.py,v 1.2 2008-06-27 02:12:00 ameyer Exp $
# $Log: not supported by cvs2svn $
# Revision 1.1  2007/10/19 04:15:44  ameyer
# Initial version.
#
#----------------------------------------------------------------------
import cdr, cdrdb, ModifyDocs, sys

#----------------------------------------------------------------------
# Filter class for ModifyDocs.
#----------------------------------------------------------------------
class Filter:
    def getDocIds(self):
        """
        Selects all doc ids from query_term_pub that have one of the
        seven SemanticTypes of interest.

        A check of Bach showed that all entries in the query_term
        table with one of the seven types also existed in the query_term_pub
        table with one of the seven types.  However there were three
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

   <!-- Is it one of the types we transform? -->
   <xsl:choose>
     <xsl:when              test = '@cdr:ref = "CDR0000539747" or
                                    @cdr:ref = "CDR0000256159" or
                                    @cdr:ref = "CDR0000256160" or
                                    @cdr:ref = "CDR0000256161" or
                                    @cdr:ref = "CDR0000256162" or
                                    @cdr:ref = "CDR0000256163" or
                                    @cdr:ref = "CDR0000482272"'>
       <!-- Replace with new one, but only if this is the first
            matching node -->
       <xsl:if            test = "not(preceding-sibling::SemanticType[
                                      @cdr:ref = 'CDR0000539747' or
                                      @cdr:ref = 'CDR0000256159' or
                                      @cdr:ref = 'CDR0000256160' or
                                      @cdr:ref = 'CDR0000256161' or
                                      @cdr:ref = 'CDR0000256162' or
                                      @cdr:ref = 'CDR0000256163' or
                                      @cdr:ref = 'CDR0000482272'])">

         <!-- Create new, empty element -->
         <xsl:copy>
           <!-- Replace cdr:ref with new one
                Don't copy PdqKey, it's no longer relevant -->
           <xsl:attribute name='cdr:ref'>CDR0000256087</xsl:attribute>

           <!-- Denormalized text isn't required, but let's do it anyway -->
           <xsl:text>Intervention/procedure</xsl:text>
         </xsl:copy>
       </xsl:if>
     </xsl:when>
     <xsl:otherwise>
       <xsl:copy-of       select = '.'/>
     </xsl:otherwise>
   </xsl:choose>
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
      "Global replace 7 different SemanticTypes with 1 - Request 3680.",
      testMode=testMode)

    # Debug
    # job.setMaxDocs(3)

    # Global change
    job.run()
