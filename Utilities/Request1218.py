#----------------------------------------------------------------------
#
# $Id$
#
# "We need to use the One-off global change mechanism to replace the
#  attached list of lead organizations with the cdrid 29246.  The
#  criteria for the change is as follows:
#  Find all protocols that have '/InScopeProtocol/ProtocolAdminInfo
#  /ProtocolLeadOrg/LeadOrganizationId/@cdr:ref' that matches the list
#  of ids in the attached file.  Replace with 29246."
#
# BZIssue::1218
#
#----------------------------------------------------------------------
import cdr, cdrdb, ModifyDocs, sys

targets = (29826, 32637, 27323, 27324, 27325, 31805, 27326, 271931,
           27327, 27328, 27329, 27331, 27322, 28760, 27332, 27333,
           27334, 27335, 34703, 30330, 33123, 30953, 27336, 27337,
           27360, 31133) # removed at Lakshmi's request, 35342)
target = "|"
for id in targets:
    target += "CDR%010d|" % id

#----------------------------------------------------------------------
# The Filter class is given to the ModifyDocs.Job object, which invokes
# the getDocIds() method to retrieve a list of CDR document IDs for
# processing.
#----------------------------------------------------------------------
class Filter:
    def getDocIds(self):
        #return [63606]
        conn = cdrdb.connect('CdrGuest')
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE #t (id INTEGER)")
        conn.commit()
        for id in targets:
            cursor.execute("INSERT INTO #t VALUES (?)", id)
            conn.commit()
        cursor.execute("""\
   SELECT DISTINCT q.doc_id
              FROM query_term q
              JOIN #t t
                ON t.id = q.int_val
             WHERE q.path = '/InScopeProtocol/ProtocolAdminInfo'
                          + '/ProtocolLeadOrg/LeadOrganizationID/@cdr:ref'""")
        return [row[0] for row in cursor.fetchall()]

#----------------------------------------------------------------------
# The Transform class is given to the ModifyDocs.Job object, which in
# turn gives it to each ModifyDocs.Doc object.  The run() method of
# this class takes a cdr.Doc object and returns a (possibly) modified
# copy of that object's xml member.
#----------------------------------------------------------------------
class Transform:
    def run(self, docObj):
        #sep = ""
        #match = 'ProtocolLeadOrg/LeadOrganizationID['
        #for id in targets:
        #    match += '%s@cdr:ref = "CDR%010d"' % (sep, id)
        #    sep = " or "
        #match += "]"
        
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
 <xsl:template                  match = 'ProtocolLeadOrg/LeadOrganizationID'>
  <xsl:variable                  name = 'docId'>
   <xsl:choose>
    <xsl:when                    test = 'contains("%s", @cdr:ref)'>
     <xsl:value-of             select = '"CDR0000029246"'/>
    </xsl:when>
    <xsl:otherwise>
     <xsl:value-of             select = '@cdr:ref'/>
    </xsl:otherwise>
   </xsl:choose>
  </xsl:variable>
  <LeadOrganizationID         cdr:ref = '{$docId}'>
   <xsl:apply-templates        select = 'node()|comment()|
                                         processing-instruction()'/>
  </LeadOrganizationID>
 </xsl:template>
</xsl:transform>
""" % target
        #print filter
        response = cdr.filterDoc('guest', filter, doc = docObj.xml, inline = 1)
        if type(response) in (type(""), type(u"")):
            raise Exception("Failure in normalizeDoc: %s" % response)
        return response[0]

job = ModifyDocs.Job(sys.argv[1], sys.argv[2], Filter(), Transform(),
                     "Lead org replacement (request #1218).")
job.run()
