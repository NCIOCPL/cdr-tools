#----------------------------------------------------------------------
#
# $Id$
#
# One off change to modify:
#   /CTGovProtocol//InterventionName
#  to:
#   /CTGovProtocol//InterventionNameLink
#
# The purpose is to make CTGovProtocol indexing fields exactly
# match InScopeProtocol indexing fields.
#
# $Log: not supported by cvs2svn $
#
#----------------------------------------------------------------------
import cdr, cdrdb, ModifyDocs, sys

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
            FROM document d, doc_type t
           WHERE d.doc_type = t.id
             AND t.name = 'CTGovProtocol'
        ORDER BY d.id""")

        # Bob's slick technique for returning the first element of
        #  each row in a sequence instead of a sequence of sequences
        return [row[0] for row in cursor.fetchall()]

#----------------------------------------------------------------------
# The Transform class is given to the ModifyDocs.Job object, which in
# turn gives it to each ModifyDocs.Doc object.  The run() method of
# this class takes a cdr.Doc object and returns a (possibly) modified
# copy of that object's xml member.
#----------------------------------------------------------------------
class Transform:
    def run(self, docObj):

        filter = """\
<?xml version='1.0' encoding='UTF-8'?>

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
   <xsl:apply-templates        select = '@*|node()|comment()|text()|
                                         processing-instruction()'/>
  </xsl:copy>
 </xsl:template>

 <!-- Replace InterventionName with InterventionNameLink -->
 <xsl:template                  match = 'Intervention/InterventionName'>
  <xsl:element                   name = 'InterventionNameLink'>
   <xsl:apply-templates        select = '@*|node()|comment()|text()|
                                         processing-instruction()'/>
  </xsl:element>
 </xsl:template>
</xsl:transform>
"""
        response = cdr.filterDoc('guest', filter, doc = docObj.xml, inline = 1)
        if type(response) in (type(""), type(u"")):
            raise Exception("Failure in normalizeDoc: %s" % response)
        return response[0]

# To run with real database update, pass userid, pw, 'run' on cmd line
testMode = True
if len(sys.argv) > 3:
    if sys.argv[3] == 'run':
        testMode = False
job = ModifyDocs.Job(sys.argv[1], sys.argv[2], Filter(), Transform(),
         "Convert InterventionName to InterventionNameLink (request #1208).",
         testMode=testMode)
job.run()
