#----------------------------------------------------------------------
# Global change to manipulate "Quality of Life" Condition, Diagnosis,
# and InterventionType.
#
# Satisfies Bugzilla request 4619.  See comments in Bugzilla for details.
#
# $Id$
#
# $Log: not supported by cvs2svn $
#
#----------------------------------------------------------------------
import sys, cdr, cdrdb, ModifyDocs

class FilterTransform:

    def getDocIds(self):
        """
        Return the list of doc IDs.
        """
        # Return relevant ids from both InScope and CTGov protocols
        conn = cdrdb.connect('CdrGuest')
        cursor = conn.cursor()

        # InScope
        cursor.execute("""
        SELECT q.doc_id, d.title
          FROM query_term q
          JOIN document d
            ON d.id = q.doc_id
         WHERE q.int_val = 42052
           AND q.path IN ('/InScopeProtocol/ProtocolDetail/Condition/@cdr:ref',
                          '/InScopeProtocol/Eligibility/Diagnosis/@cdr:ref')
         ORDER BY doc_id""")
        rows   = cursor.fetchall()
        docIds = [row[0] for row in rows]

        # CTGov
        cursor.execute("""
        SELECT q.doc_id, d.title
          FROM query_term q
          JOIN document d
            ON d.id = q.doc_id
         WHERE q.int_val = 42052
           AND q.path IN ('/CTGovProtocol/PDQIndexing/Condition/@cdr:ref',
              '/CTGovProtocol/PDQIndexing/Eligibility/Diagnosis/@cdr:ref')
         ORDER BY doc_id""")
        rows   = cursor.fetchall()
        docIds += [row[0] for row in rows]

        return docIds
        # return [445117,]


    def run(self, docObj):
        """
        Transform one doc.

        Calls different transform depending on doc type.
        """
        InProcXsl = """<?xml version='1.0' encoding='UTF-8'?>

<xsl:transform version = '1.0'
               xmlns:xsl = 'http://www.w3.org/1999/XSL/Transform'
               xmlns:cdr = 'cips.nci.nih.gov/cdr'>

 <xsl:output method = 'xml'/>

 <!-- $haveQOL      = we already have the right InterventionType
      not($haveQOL) = we don't -->
 <xsl:variable
     name = 'haveQOL'
     select = "/InScopeProtocol/ProtocolDetail/StudyCategory
               /Intervention/InterventionType[@cdr:ref = 'CDR0000042050']"/>

 <!--
 =======================================================================
 Copy almost everything straight through.
 ======================================================================= -->
 <xsl:template match = '@*|node()|comment()|
                                    processing-instruction()'>
  <xsl:copy>
   <xsl:apply-templates select = '@*|node()|comment()|text()|
                                    processing-instruction()'/>
  </xsl:copy>
 </xsl:template>

 <!-- Take no action on Condition or Diagnosis matching our criteria -->
 <xsl:template match = "/InScopeProtocol/ProtocolDetail/
                         Condition[@cdr:ref='CDR0000042052']">
 </xsl:template>
 <xsl:template match = "/InScopeProtocol/Eligibility/
                         Diagnosis[@cdr:ref='CDR0000042052']">
 </xsl:template>

 <xsl:template match = '/InScopeProtocol/ProtocolDetail/StudyCategory
                        /Intervention'>

   <!-- If this is the first Intervention and we don't have the Type
        we want, create it here -->
   <xsl:if test = '. = /InScopeProtocol/ProtocolDetail/StudyCategory[1]
                        /Intervention[1]'>
     <xsl:if test = 'not($haveQOL)'>
       <xsl:element name = 'Intervention'>
         <xsl:element name = 'InterventionType'>
           <xsl:attribute name = "cdr:ref">CDR0000042050</xsl:attribute>
         </xsl:element>
       </xsl:element>
     </xsl:if>
   </xsl:if>

   <!-- Copy everything -->
   <xsl:copy>
     <xsl:apply-templates select = '@*|node()|comment()|text()|
                                      processing-instruction()'/>
   </xsl:copy>

 </xsl:template>
</xsl:transform>
"""

        CTGovXsl = """<?xml version='1.0' encoding='UTF-8'?>

<!-- See InScopeXsl transform for comments -->
<xsl:transform version = '1.0'
               xmlns:xsl = 'http://www.w3.org/1999/XSL/Transform'
               xmlns:cdr = 'cips.nci.nih.gov/cdr'>

 <xsl:output method = 'xml'/>

 <xsl:variable
     name = 'haveQOL'
     select = "/CTGovProtocol/PDQIndexing/StudyCategory/Intervention
               /Intervention/InterventionType[@cdr:ref = 'CDR0000042050']"/>

 <xsl:template match = '@*|node()|comment()|
                                    processing-instruction()'>
  <xsl:copy>
   <xsl:apply-templates select = '@*|node()|comment()|text()|
                                    processing-instruction()'/>
  </xsl:copy>
 </xsl:template>

 <xsl:template match = "/CTGovProtocol/PDQIndexing
                        /Condition[@cdr:ref='CDR0000042052']">
 </xsl:template>
 <xsl:template match = "/CTGovProtocol/PDQIndexing/Eligibility
                        /Diagnosis[@cdr:ref='CDR0000042052']">
 </xsl:template>

 <xsl:template match = "/CTGovProtocol/PDQIndexing/StudyCategory
                        /Intervention">

   <xsl:if test = '. = /CTGovProtocol/PDQIndexing/StudyCategory[1]
                        /Intervention[1]'>
     <xsl:if test = 'not($haveQOL)'>
       <xsl:element name = 'Intervention'>
         <xsl:element name = 'InterventionType'>
           <xsl:attribute name = "cdr:ref">CDR0000042050</xsl:attribute>
         </xsl:element>
       </xsl:element>
     </xsl:if>
   </xsl:if>

   <xsl:copy>
     <xsl:apply-templates select = '@*|node()|comment()|text()|
                                      processing-instruction()'/>
   </xsl:copy>

 </xsl:template>
</xsl:transform>
"""
        # Run the filter
        if docObj.type == "InScopeProtocol":
            xsl = InProcXsl
        elif docObj.type == "CTGovProtocol":
            xsl = CTGovXsl
        else:
            raise cdr.Exception("Bad doctype = %s" % docObj.type)

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
        print("usage: Request4619.py uid pw {test|run}")
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
      "Global update of Quality-of-life Condition, Diagnosis, and " +
      "InterventionType.  Request 4619.",
      testMode=testMode)

    # Debug
    # job.setMaxDocs(5)

    # Global change
    job.run()
