#----------------------------------------------------------------------
# Global change to add RegulatoryInformation elements to InScopeProtocols
# using data extracted from an Excel spreadsheet passed on the
# command line.
#
# Data is added only if there is none in the document already.  If
# data exists in the document, it takes precedence over the spreadsheet.
#
# $Id$
#
# $Log: not supported by cvs2svn $
# Revision 1.2  2008/06/27 02:14:52  ameyer
# Fixed misspelling of element.  RegulatoryInformation, not RegulatoryInfo.
#
# Revision 1.1  2008/06/24 20:09:25  ameyer
# Initial version.
#
#
#----------------------------------------------------------------------
import cdr, ExcelReader, ModifyDocs, sys

#----------------------------------------------------------------------
# Using a single class for both Filter and Transform, so they
# can easily share information.
#----------------------------------------------------------------------
class FilterTransform:

    def __init__(self, spreadsheetFile):
        """
        Load the spreadsheet file.  Fail on errors.

        Loaded data is stored in a dictionary accessible to both the
        getDocIds() and run() methods.

        Pass:
            Filename of the spreadsheet.
        """
        # Create structure to hold the data
        self.regInfo = {}
        count        = 0

        # Load workbook.  If it fails, let the exception halt processing
        workbook = ExcelReader.Workbook(spreadsheetFile)

        # Only want the first sheet.  Users may have created more
        #  inadvertently, but all the data is in the first.
        sheet = workbook[0]

        # Read each row
        for i in range(len(sheet.rows)):
            # Extract cells
            docIdStr     = sheet[i][0]  and sheet[i][0].val  or None

            # Spreadsheet supplied for first use, June 2008
            # fdaRegulated = sheet[i][11] and sheet[i][11].val or None
            # section801   = sheet[i][12] and sheet[i][12].val or None

            # Spreadsheet supplied for next use, October 2008
            fdaRegulated = sheet[i][1] and sheet[i][1].val or None
            section801   = sheet[i][2] and sheet[i][2].val or None

            # Debug
            # print ("DocID=%s fdaReg=%s 801=%s\n" % (docIdStr, fdaRegulated,
            #                                         section801))

            # Skip labels, blank lines, anything without numeric CDR ID
            if not docIdStr:
                continue
            try:
                docId = int(docIdStr)
            except ValueError:
                continue

            # Save info
            self.regInfo[docId] = (fdaRegulated, section801)
            count += 1

        # Sanity check
        if (count < 1):
            raise Exception("No data found in spreadsheet.")

    def getDocIds(self):
        """
        Return the list of doc IDs created by the constructor.
        """
        docIds = self.regInfo.keys()
        docIds.sort()
        return docIds

    def run(self, docObj):
        """
        Transform one doc, passing parameters from the spreadsheet to
        the filter.

        If the doc already has RegulatoryInformation, the filter returns
        a message to that effect.  We then hand back the unmodified
        before filtering doc to ModifyDocs, which will notice that
        it is unchanged and not store it.

        Pass:
            Object in cdr.Doc format.
        """
        HAS_INFO = "@@REGULATORYINFO EXISTS@@"

        xsl = """<?xml version='1.0' encoding='UTF-8'?>
 <!--
 =======================================================================
 Pass:
    $fdaRegulated = "Yes" or "No"
    $section801   = "Yes" or "No"
 =======================================================================
 -->
<xsl:transform  version = '1.0'
                xmlns:xsl = 'http://www.w3.org/1999/XSL/Transform'
                xmlns:cdr = 'cips.nci.nih.gov/cdr'>
 <xsl:output    method = 'xml'/>

 <xsl:param name='fdaRegulated'/>
 <xsl:param name='section801'/>

 <!-- ==================================================================
 Copy almost everything straight through.
 ======================================================================= -->
 <xsl:template match='@*|node()|text()|comment()|processing-instruction()'>
   <xsl:copy>
       <xsl:apply-templates select='@*|node()|text()|comment()|
                                    processing-instruction()'/>
   </xsl:copy>
 </xsl:template>

 <!-- If new field already exists, abort this record -->
 <xsl:template match='/InScopeProtocol/RegulatoryInformation'>
   <xsl:message terminate='yes'>%s</xsl:message>
 </xsl:template>

 <!-- Check for any of the possible preceeding fields.
      Add the new field after the last one that can exist. -->
 <xsl:template match='/InScopeProtocol/ProtocolApproval'>

   <!-- Copy this field -->
   <xsl:copy>
       <xsl:apply-templates/>
   </xsl:copy>

   <!-- This one must exist, but only use it if none of the intervening
        optional fields exist -->
   <xsl:choose>
     <xsl:when test = '../OversightInfo|../ProtocolSponsors|../FundingInfo'>
       <!-- Don't do anything -->
     </xsl:when>
     <xsl:otherwise>
       <xsl:call-template name='addRegulatoryInfo'/>
     </xsl:otherwise>
   </xsl:choose>
 </xsl:template>

 <!-- The next three are like the last one -->
 <xsl:template match='/InScopeProtocol/OversightInfo'>
   <xsl:copy>
       <xsl:apply-templates/>
   </xsl:copy>
   <xsl:choose>
     <xsl:when test = '../ProtocolSponsors|../FundingInfo'/>
     <xsl:otherwise>
       <xsl:call-template name='addRegulatoryInfo'/>
     </xsl:otherwise>
   </xsl:choose>
 </xsl:template>

 <xsl:template match='/InScopeProtocol/ProtocolSponsors'>
   <xsl:copy>
       <xsl:apply-templates/>
   </xsl:copy>
   <xsl:choose>
     <xsl:when test = '../FundingInfo'/>
     <xsl:otherwise>
       <xsl:call-template name='addRegulatoryInfo'/>
     </xsl:otherwise>
   </xsl:choose>
 </xsl:template>

 <xsl:template match='/InScopeProtocol/FundingInfo'>
   <xsl:copy>
       <xsl:apply-templates/>
   </xsl:copy>
   <!-- Add unconditionally, no intervening elements are allowed in schema -->
   <xsl:call-template name='addRegulatoryInfo'/>
 </xsl:template>

 <!-- Add a RegulatoryInformation element with data passed in + defaults -->
 <xsl:template name='addRegulatoryInfo'>
   <xsl:element name='RegulatoryInformation'>
     <xsl:element name='FDARegulated'>
       <xsl:value-of select='$fdaRegulated'/>
     </xsl:element>
     <!-- If it's FDA regulated, add Section801 (if it exists) and default
          value for DelayedPosting -->
     <xsl:if test='$fdaRegulated="Yes"'>
       <xsl:if test='$section801'>
         <xsl:element name='Section801'>
           <xsl:value-of select='$section801'/>
         </xsl:element>
       </xsl:if>
       <xsl:element name='DelayedPosting'>No</xsl:element>
     </xsl:if>
   </xsl:element>
 </xsl:template>
</xsl:transform>
""" % HAS_INFO

        # Get relevant parts of the docObj
        docId  = cdr.exNormalize(docObj.id)[1]
        docXml = docObj.xml

        # Lookup values for this doc
        fdaRegulated = self.regInfo[docId][0] or "No"
        section801   = self.regInfo[docId][1]

        parms = [('fdaRegulated', fdaRegulated),]
        if section801:
            parms.append(('section801', section801))

        response = cdr.filterDoc('guest', xsl, doc=docXml, inline=True,
                                  parm=parms)

        # String response might be known message or error
        if type(response) in (type(""), type(u"")):
            if response.find(HAS_INFO):
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
        print("usage: Request4128.py uid pw spreadsheet_filename {test|run}")
        sys.exit(1)
    uid   = sys.argv[1]
    pw    = sys.argv[2]
    fname = sys.argv[3]

    testMode = None
    if sys.argv[4] == 'test':
        testMode = True
    elif sys.argv[4] == 'run':
        testMode = False
    else:
        sys.stderr.write('Must specify "test" or "run"')
        sys.exit(1)

    # Instantiate our object, loading the spreadsheet
    filtTrans = FilterTransform(fname)

    # Instantiate ModifyDocs job
    job = ModifyDocs.Job(uid, pw, filtTrans, filtTrans,
      "Global update of FDA Regulatory Info from spreadsheet.  Request 4128.",
      testMode=testMode)

    # Debug
    # job.setMaxDocs(10)

    # Global change
    job.run()
