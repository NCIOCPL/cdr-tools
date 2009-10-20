#----------------------------------------------------------------------
#
# $Id$
#
# We need to change values in ProtocolDesign element to match the new
# values in the enumerated list. The one-off global change harness
# will be used for this purpose:
#
#    1. Replace Randomized controlled with two occurrences of
#       ProtocolDesign with values Randomized and controlled (in
#       that order)
#
#    2. Replace Non-randomized controlled with two occurrences of
#       ProtocolDesign with values Non-randomized and controlled in
#       that order
#
#    3. Delete 'study' in ProtocolDesign elements that have Cohort
#       study and pilot study.
#
#    4. Replace Double-blind method and Single-blind method with
#       Double blind and Single blind in ProtocolDesign element.
#
# BZIssue::1763
#
#----------------------------------------------------------------------
import cdr, cdrdb, ModifyDocs, sys, re

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
     WHERE t.name = 'CTGovProtocol'""")
        return [row[0] for row in cursor.fetchall()]

#----------------------------------------------------------------------
# The Transform class is given to the ModifyDocs.Job object, which in
# turn gives it to each ModifyDocs.Doc object.  The run() method of
# this class takes a cdr.Doc object and returns a (possibly) modified
# copy of that object's xml member.
#
# See comment at top for this job's logic.
#----------------------------------------------------------------------
class Transform:
    def run(self, docObj):
        filt = """\
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

 <!-- Re-map values for ProtocolDesign. -->
 <xsl:template                  match = 'ProtocolDesign'>
  <xsl:variable                  name = 'oldValue'
                               select = 'normalize-space()'/>
  <xsl:choose>
   <xsl:when                    test = '$oldValue = "Randomized controlled"'>
    <ProtocolDesign>Randomized</ProtocolDesign>
    <ProtocolDesign>Controlled</ProtocolDesign>
   </xsl:when>
   <xsl:when                    test = '$oldValue =
                                                "Non-randomized controlled"'>
    <ProtocolDesign>Non-randomized</ProtocolDesign>
    <ProtocolDesign>Controlled</ProtocolDesign>
   </xsl:when>
   <xsl:when                    test = '$oldValue = "Cohort study"'>
    <ProtocolDesign>Cohort</ProtocolDesign>
   </xsl:when>
   <xsl:when                    test = '$oldValue = "Pilot study"'>
    <ProtocolDesign>Pilot</ProtocolDesign>
   </xsl:when>
   <xsl:when                    test = '$oldValue = "Double-blind method"'>
    <ProtocolDesign>Double blind</ProtocolDesign>
   </xsl:when>
   <xsl:when                    test = '$oldValue = "Single-blind method"'>
    <ProtocolDesign>Single blind</ProtocolDesign>
   </xsl:when>
   <xsl:otherwise>
    <xsl:copy>
     <xsl:apply-templates        select = '@*|node()|comment()|
                                         processing-instruction()'/>
    </xsl:copy>
   </xsl:otherwise>
  </xsl:choose>
 </xsl:template>
</xsl:transform>
"""
        result = cdr.filterDoc('guest', filt, doc = docObj.xml, inline = True)
        if type(result) in (str, unicode):
            raise Exception(result)
        return result[0]

if len(sys.argv) < 4 or sys.argv[3] not in ('test', 'live'):
    sys.stderr.write("usage: Request1763.py uid pwd test|live\n")
    sys.exit(1)
testMode = sys.argv[3] == 'test'
job = ModifyDocs.Job(sys.argv[1], sys.argv[2], Filter(), Transform(),
                     "Modify ProtocolDesign values (request #1763).",
                     testMode = testMode)
job.run()
