#----------------------------------------------------------------------
# One off change to add StartDate elements to InScopeProtocols
# using the earliest 'Active' Current or Previous OrgStatus
# StatusDate found in the document.
#
# $Id: Request3724.py,v 1.2 2007-11-13 22:52:00 ameyer Exp $
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2007/11/06 16:35:05  ameyer
# Initial version.
#
#----------------------------------------------------------------------
import cdr, cdrdb, ModifyDocs, sys

#----------------------------------------------------------------------
# Filter class for ModifyDocs.
#----------------------------------------------------------------------
class Filter:
    def getDocIds(self):
        """
        Selects all doc ids from pub_proc_nlm that have a status
        of Active, Temporarily Closed, Closed, or Completed, and
        have no StartDate element.

        """
        conn = cdrdb.connect('CdrGuest')
        cursor = conn.cursor()

        cursor.execute("""\
SELECT p.id, p.last_sent, p.last_status
  FROM pub_proc_nlm p
  JOIN query_term_pub qstat
    ON p.id = qstat.doc_id
 WHERE p.drop_notification IS NULL
   -- Only those with certain protocol status
   AND qstat.path = '/InScopeProtocol/ProtocolAdminInfo/CurrentProtocolStatus'
   AND qstat.value IN (
        'Active',
        'Temporarily closed',
        'Closed',
        'Completed'
   )
   -- Eliminate docs that already have StartDate
   AND p.id NOT IN (
    SELECT doc_id
      FROM query_term_pub
     WHERE path = '/InScopeProtocol/ProtocolAdminInfo/StartDate'
       AND value <> ''
   )
          SELECT doc_id
            FROM query_term_pub
           WHERE path = '/Term/SemanticType/@cdr:ref'
             AND int_val IN (539747,256160,256162,256163,482272,256161,256159)
        ORDER BY doc_id""")

        # Return the first element of each row in a sequence instead
        # of a sequence of sequences
        return [row[0] for row in cursor.fetchall()]

#----------------------------------------------------------------------
# Transformation run against each selected doc by ModifyDocs
#----------------------------------------------------------------------
class Transform:
    def run(self, docObj):

        xsl = """<?xml version='1.0' encoding='UTF-8'?>

<xsl:transform  version = '1.0'
                xmlns:xsl = 'http://www.w3.org/1999/XSL/Transform'
                xmlns:cdr = 'cips.nci.nih.gov/cdr'>
 <xsl:output    method = 'xml'/>


 <!-- ==================================================================
 Copy everything straight through.
 ======================================================================= -->
 <xsl:template             match = '@*|node()|comment()|
                                    processing-instruction()'>
  <xsl:copy>
   <xsl:apply-templates   select = '@*|node()|comment()|text()|
                                    processing-instruction()'/>
  </xsl:copy>
 </xsl:template>

 <!-- ==================================================================
 ProtocolAdminInfo
 ======================================================================= -->
 <xsl:template             match = '/InScopeProtocol/ProtocolAdminInfo'>

   <!-- Sanity check on SQL -->
   <xsl:if                  test = 'StartDate'>
     <xsl:message      terminate = 'yes'
      >Error: there is already a StartDate in this record</xsl:message>
   </xsl:if>

   <!-- Re-create ProtocolAdminInfo to contain everything -->
   <xsl:copy>

     <!-- Insert new first child with value from earliest Active StatusDate
          Examines CurrentOrgStatus and PreviousOrgStatus
          Nothing will be inserted if there isn't one with 'Active' -->
     <xsl:for-each        select = "//StatusDate[../StatusName='Active']">
       <xsl:sort          select = "."
                           order = 'ascending'/>
       <xsl:if              test = 'position() = 1'>
         <xsl:element       name = 'StartDate'>
           <xsl:attribute   name = 'DateType'>Actual</xsl:attribute>
           <xsl:value-of  select = "."/>
         </xsl:element>
       </xsl:if>
     </xsl:for-each>

     <!-- Copy the rest of the ProtocolAdminInfo -->
     <xsl:for-each        select = 'node()'>
       <xsl:copy>
         <xsl:apply-templates   select = '@*|node()|comment()|text()|
                                          processing-instruction()'/>
       </xsl:copy>
     </xsl:for-each>

   </xsl:copy>
 </xsl:template>

</xsl:transform>"""

        response = cdr.filterDoc('guest', xsl, doc=docObj.xml, inline=1)
        if type(response) in (type(""), type(u"")):
            raise Exception("Failure in filterDoc: %s" % response)
        return response[0]

if __name__ == '__main__':
    # Args
    if len(sys.argv) < 3:
        print("usage: Request3724.py uid pw {run}")
        sys.exit(1)

    # To run with real database update, pass userid, pw, 'run' on cmd line
    testMode = True
    if len(sys.argv) > 3:
        if sys.argv[3] == 'run':
            testMode = False

    # Instantiate ModifyDocs job
    job = ModifyDocs.Job(sys.argv[1], sys.argv[2], Filter(), Transform(),
      "Global add of StartDate to NLM exportable protocols.  Request 3724.",
      testMode=testMode)

    # Debug
    # job.setMaxDocs(3)

    # Global change
    job.run()
