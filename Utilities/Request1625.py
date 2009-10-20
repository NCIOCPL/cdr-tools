#----------------------------------------------------------------------
#
# $Id$
#
# We need to change values in ProtocolDesign element to match the new
# values in the enumerated list.
#
# BZIssue::1625
#
#----------------------------------------------------------------------
import cdr, cdrdb, sys, ModifyDocs

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
            SELECT DISTINCT doc_id
                       FROM query_term
                      WHERE path = '/InScopeProtocol/ProtocolDesign'""")
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

 <!-- Modify ProtocolDesign elements. -->
 <xsl:template                  match = 'ProtocolDesign'>
  <xsl:choose>
   <xsl:when                     test = '. = "Randomized controlled"'>
    <ProtocolDesign>Randomized</ProtocolDesign>
    <ProtocolDesign>Controlled</ProtocolDesign>
   </xsl:when>
   <xsl:when                     test = '. = "Non-randomized controlled"'>
    <ProtocolDesign>Non-randomized</ProtocolDesign>
    <ProtocolDesign>Controlled</ProtocolDesign>
   </xsl:when>
   <xsl:when                     test = '. = "Cohort study"'>
    <ProtocolDesign>Cohort</ProtocolDesign>
   </xsl:when>
   <xsl:when                     test = '. = "Pilot study"'>
    <ProtocolDesign>Pilot</ProtocolDesign>
   </xsl:when>
   <xsl:when                     test = '. = "Double-blind method"'>
    <ProtocolDesign>Double blind</ProtocolDesign>
   </xsl:when>
   <xsl:when                     test = '. = "Single-blind method"'>
    <ProtocolDesign>Single blind</ProtocolDesign>
   </xsl:when>
   <xsl:otherwise>
    <xsl:element                 name = 'ProtocolDesign'>
     <xsl:value-of             select = '.'/>
    </xsl:element>
   </xsl:otherwise>
  </xsl:choose>
 </xsl:template>
</xsl:transform>
"""
        result = cdr.filterDoc('guest', filter, doc = docObj.xml, inline = 1)
        if type(result) in (type(""), type(u"")):
            message = "%s: %s" % (docObj.id, result)
            if type(message) is unicode:
                message = message.encode('utf-8')
            job.log(message)
            return docObj.xml
        return result[0]

if len(sys.argv) < 3:
    sys.stderr.write("usage: %s uid pwd [LIVE]\n" % sys.argv[0])
    sys.exit(1)
testMode = len(sys.argv) < 4 or sys.argv[3] != "LIVE"
job = ModifyDocs.Job(sys.argv[1], sys.argv[2], Filter(), Transform(),
                     "Replacing ProtocolDesign values (request #1625).",
                     testMode = testMode)
job.run()
