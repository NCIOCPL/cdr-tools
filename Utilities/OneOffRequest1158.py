#----------------------------------------------------------------------
#
# $Id$
#
# This task is required to facilitate web-based updates. Persons who are 
# designated as Protocol Update Persons will need to have an UpdateMode
# element on their records. This task will be made dependent on another
# task that is assigned to Sheri, where CIAT will add the Update Mode of
# RSS for Cooperative group PUPS and External data file for NCIC PUP. I
# am assigning it to the global change component because it involves using
# the one-off change wrapper and I was not sure if it should go under
# Utility or Global change.
#
# The specifications for this task are: 
# 
# Find all Person documents that have the PersonRole of Protocol Update
# Person. In these documents, add an UpdateMode element with MailerType
# attribute of "Protocol_SandP" and value of "Mail".
#
# The logic in terms of saving versions and publishable versions that are
# part of the wrapper will still be applicable.
#
# $Log: not supported by cvs2svn $
# Revision 1.5  2004/05/17 14:43:29  bkline
# Fixed typo in document comment string (1558 -> 1158).
#
# Revision 1.4  2004/05/03 14:54:59  bkline
# Changed comment stored with document at Lakshmi's request; modified
# selection query to ensure that a document is only processed once.
#
# Revision 1.3  2004/03/31 13:46:30  bkline
# Removed testing throttle.
#
# Revision 1.2  2004/03/30 22:12:37  bkline
# Fixed typo in PDQ sponsorship mapping value.
#
# Revision 1.1  2004/03/30 18:34:52  bkline
# Job to insert UpdateMode elements in Person documents.
#
#----------------------------------------------------------------------
import cdr, cdrdb, ModifyDocs, re, sys

# Flag for second half of this request (see comment #26 for this issue).
part2 = False

#----------------------------------------------------------------------
# The Filter class is given to the ModifyDocs.Job object, which invokes
# the getDocIds() method to retrieve a list of CDR document IDs for
# processing.
#----------------------------------------------------------------------
class Filter:
    def getDocIds(self):
        conn = cdrdb.connect('CdrGuest')
        cursor = conn.cursor()
        if part2:
            query = """\
SELECT DISTINCT p.int_val AS PersonId
           FROM query_term p
           JOIN query_term r
             ON r.doc_id = p.doc_id
          WHERE p.path  = '/InScopeProtocol/ProtocolAdminInfo'
                        + '/ProtocolLeadOrg/LeadOrgPersonnel'
                        + '/Person/@cdr:ref'
            AND r.path  = '/InScopeProtocol/ProtocolAdminInfo'
                        + '/ProtocolLeadOrg/LeadOrgPersonnel'
                        + '/PersonRole'
            AND r.value = 'Update person'
            AND LEFT(p.node_loc, 12) = LEFT(r.node_loc, 12)
            AND p.doc_id NOT IN (SELECT doc_id
                                   FROM query_term
                                  WHERE path  = '/Person/PersonLocations'
                                              + '/OtherPracticeLocation'
                                              + '/PersonRole'
                                    AND value = 'Protocol update person')"""
        else:
            query = """\
                     SELECT DISTINCT r.doc_id
                       FROM query_term r
                       JOIN query_term c
                         ON r.doc_id = c.doc_id
                       JOIN query_term s
                         ON s.doc_id = r.doc_id
                      WHERE r.path   = '/Person/PersonLocations' +
                                       '/OtherPracticeLocation/PersonRole'
                        AND r.value  = 'Protocol update person'
                        AND c.path   = '/Person/PersonLocations/CIPSContact'
                        AND s.path   = '/Person/Status/CurrentStatus'
                        AND s.value  = 'Active'
                   ORDER BY r.doc_id"""
        cursor.execute(query)
        return [row[0] for row in cursor.fetchall()]



#----------------------------------------------------------------------
# The Transform class is given to the ModifyDocs.Job object, which in
# turn gives it to each ModifyDocs.Doc object.  The run() method of
# this class takes a cdr.Doc object and returns a (possibly) modified
# copy of that object's xml member.
#----------------------------------------------------------------------
class Transform:
    def __init__(self):
        pass # self.pattern = re.compile("TermName")
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

 <!-- Stick in an UpdateMode element after CIPSContact. -->
 <xsl:template                  match = 'PersonLocations/CIPSContact'>
  <xsl:copy-of                 select = '.'/>
  <xsl:if                        test = 'not(../UpdateMode
                                         [@MailerType = "Protocol_SandP"])'>
   <UpdateMode             MailerType = 'Protocol_SandP'>Mail</UpdateMode>
  </xsl:if>
 </xsl:template>
</xsl:transform>
"""
        response = cdr.filterDoc('guest', filter, doc = docObj.xml, inline = 1)
        if type(response) in (type(""), type(u"")):
            raise Exception("Failure in normalizeDoc: %s" % response)
        return response[0]
# ModifyDocs.DEBUG = 1
if len(sys.argv) > 3 and sys.argv[3] == "part2":
    part2 = True
job = ModifyDocs.Job(sys.argv[1], sys.argv[2], Filter(), Transform(),
                     "Update Mode element added because of Protocol "
                     "Update Person Role (#1158).")
job.run()
