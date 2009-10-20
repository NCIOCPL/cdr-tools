#----------------------------------------------------------------------
# Global change to add the following to selected InScopeProtocols:
#
#   Outcome/@Safety = "No"
#   ArmsOrGroups/@SingleArmOrGroupStudy = "Yes"
#   RegulatoryInformation/FDARegulated = "No"
#
# Satisfies Bugzilla requests 4525, 4526, and 4527.  See comments in
# 4525 for details.
#
# $Id$
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import sys, cdr, cdrdb, ModifyDocs

class FilterTransform:

    def getDocIds(self):
        """
        Return the list of doc IDs.

        This is simplified from an earlier approach.  It now just gets
        all documents with StudyType == "Research study".
        """
        # Select the pool of docs to process
        conn = cdrdb.connect('CdrGuest')
        cursor = conn.cursor()
        cursor.execute("""\
            SELECT a.id
              FROM active_doc a
              JOIN query_term t
                ON t.doc_id = a.id
             WHERE t.path   = '/InScopeProtocol/ProtocolDetail/StudyType'
               AND t.value  = 'Research study'
             ORDER BY a.id""")

        rows = cursor.fetchall()
        return [row[0] for row in rows]


    def run(self, docObj):
        """
        Transform one doc.

        Fields that already exist are left alone.
        """
        xsl = """<?xml version='1.0' encoding='UTF-8'?>
<xsl:transform  version = '1.0'
                xmlns:xsl = 'http://www.w3.org/1999/XSL/Transform'
                xmlns:cdr = 'cips.nci.nih.gov/cdr'>
 <xsl:output    method = 'xml'/>

 <!-- ==================================================================
 Copy almost everything straight through.
 ======================================================================= -->
 <xsl:template match='@*|node()|text()|comment()|processing-instruction()'>
   <xsl:copy>
       <xsl:apply-templates select='@*|node()|text()|comment()|
                                    processing-instruction()'/>
   </xsl:copy>
 </xsl:template>


 <!-- Add a "Safety" attribute to each Outcome that doesn't have it -->
 <xsl:template match='/InScopeProtocol/ProtocolAbstract/Professional/Outcome'>
   <xsl:choose>
     <xsl:when test = './@Safety'>
       <!-- Attribute already present, just copy input to output -->
       <xsl:copy>
         <xsl:apply-templates select = '@*|node()|text()|comment()|
                                        processing-instruction()'/>
       </xsl:copy>
     </xsl:when>
     <xsl:otherwise>
       <!-- Attribute not present, add it -->
       <xsl:element name = '{name()}'>
         <xsl:for-each select = '@*'>
           <xsl:copy-of select = '.'/>
         </xsl:for-each>
         <xsl:attribute name = 'Safety'>
           <xsl:text>No</xsl:text>
         </xsl:attribute>
         <xsl:apply-templates select = 'node()|comment()|text()|
                                        processing-instruction()'/>
       </xsl:element>
     </xsl:otherwise>
   </xsl:choose>
 </xsl:template>


 <!-- Add an ArmsOrGroups element after Outline if not already present -->
 <xsl:template match='/InScopeProtocol/ProtocolAbstract/Professional/Outline'>
   <xsl:copy>
       <xsl:apply-templates select='@*|node()|text()|comment()|
                                    processing-instruction()'/>
   </xsl:copy>
   <xsl:if test = 'not(../ArmsOrGroups)'>
     <xsl:element name = 'ArmsOrGroups'>
       <xsl:attribute name = 'SingleArmOrGroupStudy'>
         <xsl:text>Yes</xsl:text>
       </xsl:attribute>
     </xsl:element>
   </xsl:if>
 </xsl:template>


 <!-- RegulatoryInformation is harder to position because the
      elements around it are optional.  We check for preceeding elements
      in order of possible proximity and add the new element after the
      first one we find, i.e., last one that exists -->

 <xsl:template match = '/InScopeProtocol/ProtocolApproval'>

   <!-- Copy this field, it must always exist -->
   <xsl:copy>
       <xsl:apply-templates/>
   </xsl:copy>


   <!-- Only add RegulatoryInformation after it if next three don't exist -->
   <xsl:choose>
     <xsl:when test = '../OversightInfo|../ProtocolSponsors|../FundingInfo'>
       <!-- Don't do anything -->
     </xsl:when>
     <xsl:otherwise>
       <xsl:call-template name = 'addRegulatoryInfo'/>
     </xsl:otherwise>
   </xsl:choose>
 </xsl:template>

 <!-- The next three are like the last one -->
 <xsl:template match = '/InScopeProtocol/OversightInfo'>
   <xsl:copy>
       <xsl:apply-templates/>
   </xsl:copy>
   <xsl:choose>
     <xsl:when test = '../ProtocolSponsors|../FundingInfo'/>
     <xsl:otherwise>
       <xsl:call-template name = 'addRegulatoryInfo'/>
     </xsl:otherwise>
   </xsl:choose>
 </xsl:template>

 <xsl:template match = '/InScopeProtocol/ProtocolSponsors'>
   <xsl:copy>
       <xsl:apply-templates/>
   </xsl:copy>
   <xsl:choose>
     <xsl:when test = '../FundingInfo'/>
     <xsl:otherwise>
       <xsl:call-template name = 'addRegulatoryInfo'/>
     </xsl:otherwise>
   </xsl:choose>
 </xsl:template>

 <xsl:template match = '/InScopeProtocol/FundingInfo'>
   <xsl:copy>
       <xsl:apply-templates/>
   </xsl:copy>
   <!-- Add unconditionally, no intervening elements are allowed in schema -->
   <xsl:call-template name = 'addRegulatoryInfo'/>
 </xsl:template>

 <!-- Add a RegulatoryInformation element with data passed in + defaults -->
 <xsl:template name = 'addRegulatoryInfo'>
   <xsl:choose>
     <!-- If we've already got RegulatoryInformation, we're done -->
     <xsl:when test = '/InScopeProtocol/RegulatoryInformation'/>

     <!-- Else add it -->
     <xsl:otherwise>
       <xsl:element name = 'RegulatoryInformation'>
         <xsl:element name = 'FDARegulated'>
           <xsl:text>No</xsl:text>
         </xsl:element>
       </xsl:element>
     </xsl:otherwise>
   </xsl:choose>
 </xsl:template>
</xsl:transform>
"""
        # Run the filter
        response = cdr.filterDoc('guest', xsl, doc=docObj.xml, inline=True)

        # String response would be error message
        if type(response) in (type(""), type(u"")):
            # Must have gotten an error message
            raise Exception("Failure in filterDoc: %s" % response)

        # Got back a filtered doc
        return response[0]


if __name__ == '__main__':
    # Args
    if len(sys.argv) < 4:
        print("usage: Request4525.py uid pw {test|run}")
        sys.exit(1)
    uid   = sys.argv[1]
    pw    = sys.argv[2]

    testMode = None
    if sys.argv[3] == 'test':
        testMode = True
    elif sys.argv[3] == 'run':
        testMode = False
    else:
        sys.stderr.write('Must specify "test" or "run"')
        sys.exit(1)

    # Instantiate our object
    filtTrans = FilterTransform()

    # Instantiate ModifyDocs job
    job = ModifyDocs.Job(uid, pw, filtTrans, filtTrans,
      "Global update of Outcome, ArmsOrGroups, RegulatoryInformation.  " +
      "Request 4525.",
      testMode=testMode)

    # Debug
    # job.setMaxDocs(10)

    # Global change
    job.run()
