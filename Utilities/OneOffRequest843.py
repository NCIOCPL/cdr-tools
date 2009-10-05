#----------------------------------------------------------------------
#
# $Id: OneOffRequest843.py,v 1.2 2003-08-21 19:28:18 bkline Exp $
#
# CDR request number 843 to transform GlossaryTerm documents to
# match the new schema changes, introducing new Audience, Dictionary,
# and DefinitionText child elements for the GlossaryDefinition
# type.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2003/08/21 12:06:48  bkline
# Transforms GlossaryTerm documents to match new schema structure.
#
#----------------------------------------------------------------------
import cdr, cdrdb, ModifyDocs, re, sys

#----------------------------------------------------------------------
# The Filter class is given to the ModifyDocs.Job object, which invokes
# the getDocIds() method to retrieve a list of CDR document IDs for
# processing.
#----------------------------------------------------------------------
class Filter:
    def getDocIds(self):
        conn = cdrdb.connect('CdrGuest')
        cursor = conn.cursor()
        cursor.execute("""\
            SELECT d.id
              FROM document d
              JOIN doc_type t
                ON t.id = d.doc_type
             WHERE t.name = 'GlossaryTerm'""")
        return [row[0] for row in cursor.fetchall()]

#----------------------------------------------------------------------
# The Transform class is given to the ModifyDocs.Job object, which in
# turn gives it to each ModifyDocs.Doc object.  The run() method of
# this class takes a cdr.Doc object and returns a (possibly) modified
# copy of that object's xml member.
#----------------------------------------------------------------------
class Transform:
    def __init__(self):
        self.pattern = re.compile("TermName")
    def run(self, docObj):
        filter = """\
<?xml version='1.0' encoding='UTF-8'?>

<xsl:transform                version = '1.0' 
                            xmlns:xsl = 'http://www.w3.org/1999/XSL/Transform'
                            xmlns:cdr = 'cips.nci.nih.gov/cdr'>

 <xsl:output                   method = 'xml'/>

 <!--
 =======================================================================
 Copy most things straight through.
 ======================================================================= -->
 <xsl:template                  match = '@*|node()|comment()|
                                         processing-instruction()'>
  <xsl:copy>
   <xsl:apply-templates        select = '@*|node()|comment()|
                                         processing-instruction()'/>
  </xsl:copy>
 </xsl:template>

 <!-- Things to drop. -->
 <xsl:template                  match = 'GlossaryTerm/@Dictionary'/>

 <xsl:template                  match = 'TermDefinition|SpanishTermDefinition'>
  <xsl:choose>
   <xsl:when                     test = 'DefinitionText'>
    <xsl:copy>
     <xsl:apply-templates      select = '@*|node()|comment()|
                                         processing-instruction()'/>
    </xsl:copy>
   </xsl:when>
   <xsl:otherwise>
  
    <xsl:element                 name = '{name()}'>
     <DefinitionText>
      <xsl:if                    test = '../@cdr:id'>
       <xsl:attribute            name = 'cdr:id'>
        <xsl:value-of          select = '../@cdr:id'/>
       </xsl:attribute>
      </xsl:if>
      <xsl:apply-templates     select = 'node()|comment()|
                                         processing-instruction()'/>
     </DefinitionText>
     <xsl:if                     test = 'not(../@Dictionary="Exclude")'>
      <Dictionary>Cancer.gov</Dictionary>
     </xsl:if>
     <Audience>
      <xsl:choose>
       <xsl:when                 test = '@Audience="HealthProfessional"'>
        <xsl:text>Health professional</xsl:text>
       </xsl:when>
       <xsl:otherwise>
        <xsl:text>Patient</xsl:text>
       </xsl:otherwise>
      </xsl:choose>
     </Audience>
    </xsl:element>
   </xsl:otherwise>
  </xsl:choose>
 </xsl:template>
   
</xsl:transform>
"""
        response = cdr.filterDoc('guest', filter, doc = docObj.xml, inline = 1)
        if type(response) in (type(""), type(u"")):
            raise Exception("Failure in normalizeDoc: %s" % response)
        return response[0]

job = ModifyDocs.Job(sys.argv[1], sys.argv[2], Filter(), Transform(),
                     'Modified to conform to new GlossaryTerm structure')
job.run()
