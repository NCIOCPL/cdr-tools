#----------------------------------------------------------------------
#
# $Id$
#
# One off change to modify:
#
#   /InScopeProtocol/ProtocolSpecialCategory/SpecialCategory values.
#
#   3 values are changed.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2005/08/04 22:56:10  ameyer
# Convert some SpecialCategory values to revised text strings.
#
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
          SELECT doc_id
            FROM query_term
           WHERE path =
               '/InScopeProtocol/ProtocolSpecialCategory/SpecialCategory'
             AND value IN (
               'Cancer Centers Branch Avon Awardee',
               'NCI web site featured trial',
               'Treatment referral center trial'
             )
        ORDER BY doc_id""")

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

        filter = """<?xml version='1.0' encoding='UTF-8'?>

<xsl:transform                version = '1.0'
                            xmlns:xsl = 'http://www.w3.org/1999/XSL/Transform'
                            xmlns:cdr = 'cips.nci.nih.gov/cdr'>

 <xsl:output                   method = 'xml'/>

 <!--
 =======================================================================
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
 <xsl:template             match =
                    'InScopeProtocol/ProtocolSpecialCategory/SpecialCategory'>

   <!-- Replace the element with new or same value -->
   <xsl:element             name = "SpecialCategory">

   <!-- Searching for specific values we need to modify -->
   <xsl:choose>
     <xsl:when              test = ". = 'Cancer Centers Branch Avon Awardee'">
       <xsl:text>NCI Avon award trial</xsl:text>
     </xsl:when>
     <xsl:when              test = ". = 'NCI web site featured trial'">
       <xsl:text>NCI Web site featured trial</xsl:text>
     </xsl:when>
     <xsl:when              test = ". = 'Treatment referral center trial'">
       <xsl:text>Treatment Referral Center (TRC) trial</xsl:text>
     </xsl:when>

     <!-- Leave the rest alone -->
     <xsl:otherwise>
       <xsl:value-of        select = "."/>
     </xsl:otherwise>
   </xsl:choose>
   </xsl:element>

 </xsl:template>
</xsl:transform>
"""
        response = cdr.filterDoc('guest', filter, doc = docObj.xml, inline = 1)
        if type(response) in (type(""), type(u"")):
            raise Exception("Failure in normalizeDoc: %s" % response)
        return response[0]

# To run with real database update, pass userid, pw, 'run' on cmd line
if len(sys.argv) < 3:
    sys.stderr.write("usage: Request1792.py userid pw {'run' - for non-test}\n")
    sys.exit(1)

testMode = True
if len(sys.argv) > 3:
    if sys.argv[3] == 'run':
        testMode = False
job = ModifyDocs.Job(sys.argv[1], sys.argv[2], Filter(), Transform(),
         "Global change 3 SpecialCategory values (request #1792).",
         testMode=testMode)
job.run()
