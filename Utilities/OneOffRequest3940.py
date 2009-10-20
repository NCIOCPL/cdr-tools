#----------------------------------------------------------------------
#
# $Id$
#
# The trials on the attached list need to have <UpdateMode> with 'Oncore'
# added to the <ProtocolLeadOrg> with <LeadOrgRole> type of Primary.
#
# BZIssue::3940
#
#----------------------------------------------------------------------
import cdr, cdrdb, ModifyDocs, re, sys, ExcelReader

#----------------------------------------------------------------------
# The Filter class is given to the ModifyDocs.Job object, which invokes
# the getDocIds() method to retrieve a list of CDR document IDs for
# processing.
#----------------------------------------------------------------------
class Filter:
    def __init__(self, filename):
        ids = set()
        conn = cdrdb.connect('CdrGuest')
        cursor = conn.cursor()
        book = ExcelReader.Workbook(filename)
        sheet = book[0]
        for row in sheet:
            docId = row[0].val
            if docId and docId.startswith('CDR'):
                docId = int(re.sub(u'[^\\d]+', u'', docId))
                cursor.execute("""\
                    SELECT t.name
                      FROM doc_type t
                      JOIN document d
                        ON d.doc_type = t.id
                     WHERE d.id = ?""", docId)
                rows = cursor.fetchall()
                if not rows:
                    sys.stderr.write("%s not found\n" % row[0].val)
                elif rows[0][0] != 'InScopeProtocol':
                    sys.stderr.write("%s is a %s document\n" % (row[0].val,
                                                                rows[0][0]))
                else:
                    ids.add(docId)
        self.ids = list(ids)
        self.ids.sort()
        sys.stderr.write("collected ids %s\n" % self.ids)
    def getDocIds(self):
        return self.ids

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

 <!-- Stick in an UpdateMode element at the end of the primary lead org's
      block. -->
 <xsl:template                  match = 'ProtocolLeadOrg'>
  <xsl:copy>
   <xsl:apply-templates        select = '@*|node()|comment()|
                                         processing-instruction()'/>
   <xsl:if                       test = 'LeadOrgRole = "Primary"'>
    <UpdateMode            MailerType = 'Protocol_SandP'>Oncore</UpdateMode>
   </xsl:if>
  </xsl:copy>
 </xsl:template>
</xsl:transform>
"""
        response = cdr.filterDoc('guest', filter, doc = docObj.xml, inline = 1)
        if type(response) in (str, unicode):
            raise Exception(u"Failure in normalizeDoc: %s" % response)
        return response[0]
filename = len(sys.argv) > 3 and sys.argv[3] or "Request3940.xls"
job = ModifyDocs.Job(sys.argv[1], sys.argv[2], Filter(filename), Transform(),
                     "Update Mode of 'Oncore' added (#3940)",
                     testMode = False)
job.run()
