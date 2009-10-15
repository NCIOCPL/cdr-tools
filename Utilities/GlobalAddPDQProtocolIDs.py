#----------------------------------------------------------------------
# Global change to insert the ProtocolIDs element from an InScopeProtocol
# into the CTGovProtocol that has replaced it.
#
# Finds all pairs of protocols where a CTGovProtocol has replaced an
# InScopeProtocol and, if the change has not already been made, makes it.
#
# Satisfies Bugzilla request 4634.  See comments in Bugzilla for details.
# BZIssue:4634
#
# $Id$
#
#                                           Author: Alan Meyer
#                                           Date: October, 2009
#----------------------------------------------------------------------
import sys, cdr, cdrdb, ModifyDocs

# Query to find pairs of InScope and CTGov protocol IDs.
findDocsQry = """
-- Find inactive InScope doc CDR IDs with an associated nct_id
  SELECT InScopeQ.doc_id, CTGovQ.doc_id
    FROM query_term InScopeQ
    JOIN query_term NctIdQ
      ON InScopeQ.doc_id = NctIdQ.doc_id
     AND LEFT(InScopeQ.node_loc, 8) = LEFT(NctIdQ.node_loc, 8)
    JOIN query_term CTGovQ
      ON CTGovQ.value = InScopeQ.value
    JOIN all_docs d
      ON InScopeQ.doc_id = d.id
   WHERE InScopeQ.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDString'
     AND NctIdQ.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
     AND NctIdQ.value = 'ClinicalTrials.gov ID'
     AND CTGovQ.path = '/CTGovProtocol/IDInfo/NCTID'
     AND d.active_status = 'I'
     -- Following will work if we index the required path
     -- Otherwise, no harm done
     AND CTGovQ.doc_id NOT IN (
        SELECT doneQ.doc_id
          FROM query_term doneQ
         WHERE doneQ.path = '/CTGovProtocol/PDQProtocolIDs/PrimaryID'
	 )
   ORDER BY CTGovQ.doc_id
"""

# Filter returns this if doc already has PDQProtocolIDs block
HAS_PDQIDS = "@@PDQProtocolIDs ALREADY INSERTED@@"

# Here's the filter
transformXml = """<?xml version='1.0' encoding='UTF-8'?>
 <!--
 =======================================================================
 Pass:
    $inScopeDocID = CDR ID of InScopeProtocol with ProtocolIDs to copy
                    into this CTGovProtocol
 =======================================================================
 -->
<xsl:transform  version = '1.0'
                xmlns:xsl = 'http://www.w3.org/1999/XSL/Transform'
                xmlns:cdr = 'cips.nci.nih.gov/cdr'>
 <xsl:output    method = 'xml'/>

 <xsl:param name='inScopeDocID'/>

 <!-- Get the PDQProtocolIDs element from the InScopeProtocol, ready for
      insertion into the current CTGovProtocol -->
 <xsl:variable name='PDQ_IDs' select='document(concat("cdr:",$inScopeDocID))'/>

 <!--
 ==================================================================
      Copy almost everything straight through.
 ==================================================================
 -->
 <xsl:template match='@*|node()|text()|comment()|processing-instruction()'>
   <xsl:copy>
       <xsl:apply-templates select='@*|node()|text()|comment()|
                                    processing-instruction()'/>
   </xsl:copy>
 </xsl:template>

 <!-- If new field already exists, abort this record -->
 <xsl:template match='/CTGovProtocol/PDQProtocolIDs'>
   <xsl:message terminate='yes'>%s</xsl:message>
 </xsl:template>

 <!-- Placement strategy:
       There are currently 10 optional elements before the slot for
         PDQProtocolIDs and 3 optional elements after.
       We'll walk forwards from the first optional succeeding field to the
         last one, and insert the new element before the first of these that
         we see.
       VerificationDate is the first required element after PDQProtocolIDs.
  -->

 <xsl:template match='/CTGovProtocol/VerificationDate'>
   <xsl:choose>
     <!-- This one must exist but don't use it if a preceding optional
          element exists -->
     <xsl:when test='../ProtocolRelatedLinks |
                     ../CTReference          |
                     ../CTResultsReference'>
       <!-- Don't insert the new element.  It has already been inserted. -->
     </xsl:when>
     <xsl:otherwise>
       <!-- Copy in the new element -->
       <xsl:call-template name='copyProtocolIDs'/>
     </xsl:otherwise>
   </xsl:choose>
   <xsl:copy>
     <!-- Copy this VerificationDate element -->
     <xsl:apply-templates/>
   </xsl:copy>
 </xsl:template>

 <!-- Same processing concept for each of the optional fields -->
 <xsl:template match='/CTGovProtocol/CTResultsReference'>
   <xsl:choose>
     <!-- We should only add the PDQProtocolIDs once.
          The preceding-sibling test checks to be sure there are no
            preceding CTResultsReference elements.
          If there are, don't add anything here, we've already added
            the PDQProtocolIDs before the first occurrence of this element
          The same logic appears on the other repeating element, i.e.,
            CTReference.
     -->
     <xsl:when test='../ProtocolRelatedLinks |
                     ../CTReference          |
                     preceding-sibling::CTResultsReference[1]'>
     </xsl:when>
     <xsl:otherwise>
       <xsl:call-template name='copyProtocolIDs'/>
     </xsl:otherwise>
   </xsl:choose>
   <xsl:copy>
     <xsl:apply-templates/>
   </xsl:copy>
 </xsl:template>

 <xsl:template match='/CTGovProtocol/CTReference'>
   <xsl:choose>
     <!-- See comment for CTResultsReference -->
     <xsl:when test='../ProtocolRelatedLinks |
                     preceding-sibling::CTReference[1]'>
     </xsl:when>
     <xsl:otherwise>
       <xsl:call-template name='copyProtocolIDs'/>
     </xsl:otherwise>
   </xsl:choose>
   <xsl:copy>
     <xsl:apply-templates/>
   </xsl:copy>
 </xsl:template>

 <xsl:template match='/CTGovProtocol/ProtocolRelatedLinks'>
   <!-- If we have this element, new elem comes before it, unconditionally -->
   <xsl:call-template name='copyProtocolIDs'/>
   <xsl:copy>
     <xsl:apply-templates/>
   </xsl:copy>
 </xsl:template>


 <xsl:template name='copyProtocolIDs'>
   <!-- We're positioned to insertion point.
        Put in the ProtocolIDs -->
   <xsl:element name='PDQProtocolIDs'>
     <!-- Copy contents from InScopeProtocol by using the above copy rule -->
     <xsl:apply-templates select='($PDQ_IDs)//ProtocolIDs/*'/>
   </xsl:element>
 </xsl:template>
</xsl:transform>
""" % HAS_PDQIDS

class FilterTransform:

    def __init__(self):
        pass

    def getDocIds(self):
        """
        Find all pairs of InScope and CTGov protocols that share the same
        NCTIDs.

        We store the pairs in memory.  CTGovProtocol IDs will be given to
        the ModifyDocs module to select docs to be modified.  The transform
        routine will use the pairs to look up the corresponding
        InScopeProtocol from which to extract IDs for transfer to our
        version of the CTGovProtocol.
        """
        global findDocsQry
        # Search
        try:
            conn = cdrdb.connect()
            cursor = conn.cursor()
            cursor.execute(findDocsQry, timeout=180)
            rows = cursor.fetchall()
            cursor.close()
        except cdrdb.Error, info:
            cdr.logwrite("Error finding docs: %s" % info)
            sys.exit(1)

        # Create a lookup table, CTGov CDRID -> InScope CDRID
        self.lookup = {}
        for row in rows:
            self.lookup[row[1]] = row[0]

        # Return CTGovProtocol CDR IDs, in CDR ID order
        return [row[1] for row in rows]
        # return [553674,643541]

    def run(self, docObj):
        """
        Transform one CTGovProtocol document.

        Find the associated InScopeProtocol doc, read it in (via the XSLT
        document() function) and transfer the ProtocolIDs block.
        """
        # Get CTGov integer CDR ID and XML plus InScope integer ID
        ctGovDocId   = cdr.exNormalize(docObj.id)[1]
        docXml       = docObj.xml
        inScopeDocId = self.lookup[ctGovDocId]

        # Filter the CTGov doc, passing InScope ID as a parameter
        parms = [['inScopeDocID', cdr.exNormalize(inScopeDocId)[0]]]
        response = cdr.filterDoc('guest', transformXml, doc=docXml,
                                  inline=True, parm=parms)

        # String response might be known message or error
        if type(response) in (type(""), type(u"")):
            if response.find(HAS_PDQIDS):
                # Return unmodified XML.  No change needed
                return docXml
            else:
                # Must have gotten an error message
                raise Exception("Failure in filterDoc: %s" % response)

        # Got back a filtered doc
        return response[0]


if __name__ == '__main__':
    # Args
    if len(sys.argv) < 4:
        print("usage: GlobalAddPDQProtocolIDs.py uid pw {test|run}")
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

    # Instantiate our object, loading the spreadsheet
    filtTrans = FilterTransform()

    # Instantiate ModifyDocs job
    job = ModifyDocs.Job(uid, pw, filtTrans, filtTrans,
      "Global update of CTGovProtocols with PDQProtocolIDs.  Request 4634.",
      testMode=testMode)

    # Debug
    # job.setMaxDocs(2)

    # Global change
    job.run()
