#----------------------------------------------------------------------
#
# $Id: Request1349.py,v 1.1 2004-10-11 12:40:46 bkline Exp $
#
# Actually after thinking a little more about this, I was wondering why
# we should not remove the PUP role altogether if the person has more
# than one role and also remove the Person link altogether. What do you
# think? I don't think we have any special validation that requires the
# presence of the Update Person role
#
# There are two possible data scenarios here:
#
# 1. One LeadOrgPersonnel element with two PersonRole elements with values 
# of "Protocol Chair" or "Prinicipal Investigator" and "Update Person".
#
# 2. Two LeadOrgPersonnel elements -- one with PersonRole of Update Person and 
# another with PersonRole of Protocol Chair or Prinicpal Investigator.
#
# In the first scenario, we would take out the LeadOrgPersonnel/PersonRole 
# element with value of Update Person. This would leave the 
# LeadOrgPersonnel/Person and the PersonRole element in tact -- no validity 
# issues.
#
# In the second scenario, we would take out the LeadOrgPerson block where the 
# PersonRole element had the value Update Person. In this case there would be 
# another LeadOrgPersonnel block that would still be there -- not validity
# issues.
#
# If it finds a lead org that only has one lead org person, and that
# person has only one role, and that role is "Update Person" then
# the program would do nothing. I don't think we will encounter 
# that use case (unless the protocol is midway through being processed).
# Can the program report these instances? CIAT can then fix manually.
#
# $Log: not supported by cvs2svn $
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
SELECT DISTINCT q.doc_id
           FROM query_term q
           JOIN doc_version v
             ON v.id = q.doc_id
          WHERE q.int_val IN (32676, 30265, 35676, 36120,
                              36176, 35709, 36149, 35883)
            AND q.path = '/InScopeProtocol/ProtocolAdminInfo'
                       + '/ProtocolLeadOrg/LeadOrganizationID/@cdr:ref'
            AND v.publishable = 'Y'""")
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
 <xsl:variable                   name = 'orgList'
                               select = '"CDR0000032676 CDR0000030265
                                          CDR0000035676 CDR0000036120
                                          CDR0000036176 CDR0000035709
                                          CDR0000036149 CDR0000035883"'/>

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

 <!-- Extract organization ID, without fragment ID. -->
 <xsl:template                   name = 'extractOrgId'>
  <xsl:param                     name = 'ref'/>
  <xsl:choose>
   <xsl:when                     test = 'contains($ref, "#")'>
    <xsl:value-of              select = 'substring-before($ref, "#")'/>
   </xsl:when>
   <xsl:when                     test = 'not($ref) or $ref = ""'>
    <xsl:value-of              select = '"NO-ID"'/>
   </xsl:when>
   <xsl:otherwise>
    <xsl:value-of              select = '$ref'/>
   </xsl:otherwise>
  </xsl:choose>
 </xsl:template>

 <!-- Special handling for certain protocol lead org persons. -->
 <xsl:template                  match = 'ProtocolLeadOrg/LeadOrgPersonnel'>
  <xsl:variable                  name = 'orgId'>
   <xsl:call-template            name = 'extractOrgId'>
    <xsl:with-param              name = 'ref'
                               select = '../LeadOrganizationID/@cdr:ref'/>
   </xsl:call-template>
  </xsl:variable>
  <xsl:if                        test = 'not(contains($orgList, $orgId)) or
                                          PersonRole != "Update person" or
                                          not(../LeadOrgPersonnel
                                            [PersonRole != "Update person"])'>
   <xsl:copy>
    <xsl:apply-templates       select = '@*|node()|comment()|
                                         processing-instruction()'/>
   </xsl:copy>
  </xsl:if>
 </xsl:template>

 <!-- Special processing for lead org personnel roles. -->
 <xsl:template                  match = 'LeadOrgPersonnel/PersonRole'>
  <xsl:variable                  name = 'orgId'>
   <xsl:call-template            name = 'extractOrgId'>
    <xsl:with-param              name = 'ref'
                               select = '../../LeadOrganizationID/@cdr:ref'/>
   </xsl:call-template>
  </xsl:variable>
  <xsl:choose>
   <xsl:when                     test = 'contains($orgList, $orgId) and
                                         . = "Update person"'>
    <xsl:if                      test = 'not(../../LeadOrgPersonnel
                                         [PersonRole != "Update person"])'>
     <xsl:message>Lead org has only PUPs</xsl:message>
     <xsl:copy>
      <xsl:apply-templates     select = '@*|node()|comment()|
                                         processing-instruction()'/>
     </xsl:copy>
    </xsl:if>
   </xsl:when>
   <xsl:otherwise>
    <xsl:copy>
     <xsl:apply-templates      select = '@*|node()|comment()|
                                         processing-instruction()'/>
    </xsl:copy>
   </xsl:otherwise>
  </xsl:choose>
 </xsl:template>
</xsl:transform>
"""
        response = cdr.filterDoc('guest', filter, doc = docObj.xml, inline = 1)
        if type(response) in (type(""), type(u"")):
            raise Exception("Failure in normalizeDoc: %s" % response)
        if response[1]:
            job.log("%s: lead org with only PUP" % docObj.id)
        return response[0]

job = ModifyDocs.Job(sys.argv[1], sys.argv[2], Filter(), Transform(),
                     "Drop PUPs (request #1349).", testMode = False)
job.run()
