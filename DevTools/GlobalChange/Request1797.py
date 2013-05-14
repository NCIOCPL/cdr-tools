#----------------------------------------------------------------------
#
# $Id$
#
# We need to add UpdateMode with value of 'COG' in the
# InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg block where the
# sibling LeadOrganizationID has cdr:ref attribute of 33155.
#
# BZIssue::1797
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
    SELECT DISTINCT doc_id
               FROM query_term
              WHERE path = '/InScopeProtocol/ProtocolAdminInfo'
                         + '/ProtocolLeadOrg/LeadOrganizationID/@cdr:ref'
                AND int_val = 33155
           ORDER BY doc_id""")
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

 <!-- Drop UpdateMode for COG as lead org. -->
 <xsl:template                  match = 'UpdateMode'>
  <xsl:if                        test = 'not(@MailerType = "Protocol_SandP"
                                         and ../LeadOrganizationID/@cdr:ref
                                         = "CDR0000033155")'>
   <xsl:copy>
    <xsl:apply-templates       select = '@*|node()|comment()|
                                         processing-instruction()'/>
   </xsl:copy>
  </xsl:if>
 </xsl:template>

 <!-- Insert new UpdateMode element for COG. -->
 <xsl:template                  match = 'ProtocolLeadOrg'>
  <xsl:element                   name = 'ProtocolLeadOrg'>
   <xsl:apply-templates        select = '@*|node()|comment()|
                                         processing-instruction()'/>
   <xsl:if                       test = 'LeadOrganizationID/@cdr:ref =
                                         "CDR0000033155"'>
    <UpdateMode            MailerType = 'Protocol_SandP'>COG</UpdateMode>
   </xsl:if>
  </xsl:element>
 </xsl:template>

</xsl:transform>
"""
        result = cdr.filterDoc('guest', filt, doc = docObj.xml, inline = True)
        if type(result) in (str, unicode):
            raise Exception(result)
        return result[0]

if len(sys.argv) < 4 or sys.argv[3] not in ('test', 'live'):
    sys.stderr.write("usage: Request1797.py uid pwd test|live\n")
    sys.exit(1)
testMode = sys.argv[3] == 'test'
job = ModifyDocs.Job(sys.argv[1], sys.argv[2], Filter(), Transform(),
                     "Insert COG UpdateMode (request #1797).",
                     testMode = testMode)
job.run()
