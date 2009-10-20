#----------------------------------------------------------------------
#
# $Id$
#
# Populates NCIC OtherID values.
#
# Comment #16:
# "Attached is a file with the CDRID next to the filenames (spreadsheet
# form), so that Bob can globally add the value of Institutional/Orginal
# to the documents.  There are some blanks in the file for trials that we
# do not have."
#
# Comment #18:
# "Here's the approach I think we agreed on in today's meeting.
#
# 1. I will modify the OtherID element to carry an optional attribute
#    named 'Institution'.
# 2. I will populate this attribute with 'NCIC' for the documents
#    modified by this task.  For example:
#
# <OtherID Institution='NCIC'>
#  <IDType>Institutional/Original</IDType>
#  <IDString>br8</IDString>
# </OtherID>"
#
# BZIssue::2718
#
#----------------------------------------------------------------------
import cdr, cdrdb, re, sys, ModifyDocs, ExcelReader, cgi

#----------------------------------------------------------------------
# The Filter class is given to the ModifyDocs.Job object, which invokes
# the getDocIds() method to retrieve a list of CDR document IDs for
# processing.
#----------------------------------------------------------------------
class Filter:
    def __init__(self, trials):
        self.ids = trials.keys()
    def getDocIds(self):
        return self.ids

#----------------------------------------------------------------------
# The Transform class is given to the ModifyDocs.Job object, which in
# turn gives it to each ModifyDocs.Doc object.  The run() method of
# this class takes a cdr.Doc object and returns a (possibly) modified
# copy of that object's xml member.
#
# See comment at top for this job's logic.
#----------------------------------------------------------------------
class Transform:
    def __init__(self, trials):
        self.trials = trials
    def run(self, docObj):
        docIds = cdr.exNormalize(docObj.id)
        docId  = docIds[1]
        filt   = """\
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

 <!-- Insert new Gender element immediately after required AgeText. -->
 <xsl:template                  match = 'ProtocolIDs'>
  <xsl:copy>
   <xsl:apply-templates        select = '@*|node()|comment()|
                                         processing-instruction()'/>
   <xsl:if                       test = 'not(OtherID[
                                         IDType = "Institutional/Original"])'>
<!-- testing not(xxx[yyy="zzz"]) syntax
   <xsl:if                       test = 'not(OtherID[
                                         IDType = "Secondary"])'>
-->
    <OtherID              Institution = 'NCIC'>
     <IDType>Institutional/Original</IDType>
     <IDString>%s</IDString>
    </OtherID>
   </xsl:if>
  </xsl:copy>
 </xsl:template>
 <xsl:template                  match = 'OtherID'>
  <xsl:copy>
   <xsl:if                       test = 'IDType = "Institutional/Original"'>
    <xsl:attribute               name = 'Institution'>NCIC</xsl:attribute>
   </xsl:if>
   <xsl:apply-templates        select = '@*|node()|comment()|
                                         processing-instruction()'/>
  </xsl:copy>
 </xsl:template>
</xsl:transform>
""" % trials[docId]
        result = cdr.filterDoc('guest', filt, doc = docObj.xml, inline = True)
        if type(result) in (str, unicode):
            raise Exception(result)
        return result[0]

#----------------------------------------------------------------------
# Collect the data to be added to the protocol docs.
#----------------------------------------------------------------------
if len(sys.argv) < 5 or sys.argv[4] not in ('test', 'live'):
    sys.stderr.write("usage: Request2718.py uid pwd workbook test|live\n")
    sys.exit(1)
bookName = sys.argv[3]
workbook = ExcelReader.Workbook(bookName)
sheet    = workbook[0]
trials   = {}
for row in sheet:
    try:
        ncicDocName = str(row[0].val)
        cdrId       = int(row[1].val)
        if ncicDocName.upper().endswith(".XML"):
            trials[cdrId] = ncicDocName[:-4].upper()
        else:
            trials[cdrId] = ncicDocName.upper()
    except:
        pass
sys.stderr.write("loaded %d trial IDs\n" % len(trials))
testMode        = sys.argv[4] == 'test'
filterObject    = Filter(trials)
transformObject = Transform(trials)
job = ModifyDocs.Job(sys.argv[1], sys.argv[2], filterObject, transformObject,
                     "Adding NCIC trial IDs (request #2718).",
                     testMode = testMode)
sys.stdout.flush()
job.run()
