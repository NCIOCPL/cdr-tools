#----------------------------------------------------------------------
#
# $Id$
#
# "OrgSiteID (in the InScopeProtocol XML) has been defined as an
# OrganizationLink not an OrganizationFragmentLink. However, at
# conversion time we had converted this element with links to
# fragments. When we create the XML for the Emailer document,
# can we drop the fragmentID. It seems that for orgsites that
# have the fragment ID it shows up in the diff because the update
# drops the ID. If you think we should address this in the data
# itself by running a global one-off change that would take out
# the fragments please let me know."
#
# BZIssue::1260
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
 SELECT DISTINCT doc_id
            FROM query_term
           WHERE path = '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg'
                      + '/ProtocolSites/OrgSite/OrgSiteID/@cdr:ref'
             AND value LIKE '%#%'
        ORDER BY doc_id""")
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
 Copy most things straight through.
 ======================================================================= -->
 <xsl:template                  match = '@*|node()|comment()|
                                         processing-instruction()'>
  <xsl:copy>
   <xsl:apply-templates        select = '@*|node()|comment()|
                                         processing-instruction()'/>
  </xsl:copy>
 </xsl:template>

 <!-- Swap out old lead org for new. -->
 <xsl:template                  match = 'ProtocolSites/OrgSite/OrgSiteID'>
  <xsl:variable                  name = 'docId'>
   <xsl:choose>
    <xsl:when                    test = 'contains(@cdr:ref, "#")'>
     <xsl:value-of             select = 'substring-before(@cdr:ref, "#")'/>
    </xsl:when>
    <xsl:otherwise>
     <xsl:value-of             select = '@cdr:ref'/>
    </xsl:otherwise>
   </xsl:choose>
  </xsl:variable>
  <OrgSiteID                  cdr:ref = '{$docId}'>
   <xsl:apply-templates        select = '@PdqKey|node()|comment()|
                                         processing-instruction()'/>
  </OrgSiteID>
 </xsl:template>
</xsl:transform>
"""
        response = cdr.filterDoc('guest', filter, doc = docObj.xml, inline = 1)
        if type(response) in (type(""), type(u"")):
            raise Exception("Failure in normalizeDoc: %s" % response)
        return response[0]

job = ModifyDocs.Job(sys.argv[1], sys.argv[2], Filter(), Transform(),
                     "Strip org site fragment ID (request #1260).")
job.run()
