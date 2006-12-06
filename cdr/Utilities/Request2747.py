#----------------------------------------------------------------------
# One off change to modify three Spanish strings found in GlossaryTerm
# Insertion markup for SpanishTermDefinition/DefinitionText.
#
# The strings are searched in order of most specific to most general.
#
# Written for Bugzilla issue #2747.
#
# $Id: Request2747.py,v 1.1 2006-12-06 04:55:11 ameyer Exp $
#
# $Log: not supported by cvs2svn $
#
#----------------------------------------------------------------------
import cdr, cdrdb, ModifyDocs, sys

#----------------------------------------------------------------------
# Filter class for ModifyDocs.
#----------------------------------------------------------------------
class Filter:
    def getDocIds(self):
        """
        It's not practical to select the specific docs in SQL because of
        the occurrence of variable line breaks and spacings in the
        fields of interest.

        The selection below will narrow it down however, retrieving all
        of the docs of interest to us and not too many extra ones.
        """
        conn = cdrdb.connect('CdrGuest')
        cursor = conn.cursor()
        # cursor.execute("""\
        #   SELECT d.id
        #     FROM document d
        #     JOIN doc_type t
        #       ON d.doc_type = t.id
        #    WHERE t.name = 'GlossaryTerm'
        #      AND d.xml LIKE
        #       '%<Insertion%<SpanishTermDefinition%<DefinitionText%estudio%'
        # ORDER BY d.id""", timeout=300)
        cursor.execute("""\
          SELECT d.id
            FROM document d
           WHERE d.doc_type=26
             AND d.xml LIKE
              '%<Insertion%<SpanishTermDefinition%<DefinitionText%estudio%'
        ORDER BY d.id""")

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

 <!-- Global variables for text to search for and replace -->
 <xsl:variable  name='find1'
                select='"bajo estudio para el tratamiento del"'/>
 <xsl:variable  name='replace1'
                select='"en estudio para el tratamiento de"'/>
 <xsl:variable  name='find2'
                select='"bajo estudio en el tratamiento"'/>
 <xsl:variable  name='replace2'
                select='"en estudio para el tratamiento"'/>
 <xsl:variable  name='find3'
                select='"bajo estudio"'/>
 <xsl:variable  name='replace3'
                select='"en estudio"'/>
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
 <xsl:template  match =
           '/GlossaryTerm/Insertion/SpanishTermDefinition/DefinitionText'>
   <xsl:variable name = "normStr" select = "normalize-space(.)"/>

   <!-- Does it have the text we want to edit? -->
   <xsl:choose>

     <xsl:when  test='contains($normStr, $find1)'>
       <xsl:value-of select='substring-before($normStr, $find1)'/>
       <xsl:value-of select='$replace1'/>
       <xsl:value-of select='substring-after($normStr, $find1)'/>
     </xsl:when>

     <xsl:when  test='contains($normStr, $find2)'>
       <xsl:value-of select='substring-before($normStr, $find2)'/>
       <xsl:value-of select='$replace2'/>
       <xsl:value-of select='substring-after($normStr, $find2)'/>
     </xsl:when>

     <xsl:when  test='contains($normStr, $find3)'>
       <xsl:value-of select='substring-before($normStr, $find3)'/>
       <xsl:value-of select='$replace3'/>
       <xsl:value-of select='substring-after($normStr, $find3)'/>
     </xsl:when>

     <xsl:otherwise>
       <!-- Copy it to the output record -->
       <xsl:copy>
        <xsl:apply-templates  select = "@*|comment()|*|
                                        processing-instruction()|text()"/>
       </xsl:copy>
     </xsl:otherwise>

   </xsl:choose>
 </xsl:template>
</xsl:transform>
"""
        response = cdr.filterDoc('guest', xsl, doc = docObj.xml, inline = 1)
        if type(response) in (type(""), type(u"")):
            raise Exception("Failure in normalizeDoc: %s" % response)
        return response[0]

# Note: Testing for main enables pychecker import without running
if __name__ == '__main__':
    # To run with real database update, pass userid, pw, 'run' on cmd line
    testMode = True
    if len(sys.argv) > 3:
        if sys.argv[3] == 'run':
            testMode = False

    # Instantiate ModifyDocs job
    job = ModifyDocs.Job(sys.argv[1], sys.argv[2], Filter(), Transform(),
          "Convert InterventionName to InterventionNameLink (request #1208).",
           testMode=testMode)

    # Turn off all modifications except for Current Working Document
    ModifyDocs.setTransformANY(False)
    ModifyDocs.setTransformPUB(False)

    # Global change
    job.run()
