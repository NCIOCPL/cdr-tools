#----------------------------------------------------------------------
#
# $Id$
#
# Global insert of SingleArmOrGroupStudy attribute.
#
# Request from Shseri:
#
# "Please add the SingleArmOrGroupStudy attribute in the ArmsOrGroups block to
# selected InScopeProtocol documents that do not currently have this block and
# version the documents. (Will attach spreadsheet)."
#
# BZIssue::4189
#
#----------------------------------------------------------------------
import cdr, sys, ModifyDocs, ExcelReader

#----------------------------------------------------------------------
# The Filter class is given to the ModifyDocs.Job object, which invokes
# the getDocIds() method to retrieve a list of CDR document IDs for
# processing.
#----------------------------------------------------------------------
class Filter:
    def __init__(self, docIds):
        self.docIds = docIds
    def getDocIds(self):
        return self.docIds

#----------------------------------------------------------------------
# The Transform class is given to the ModifyDocs.Job object, which in
# turn gives it to each ModifyDocs.Doc object.  The run() method of
# this class takes a cdr.Doc object and returns a (possibly) modified
# copy of that object's xml member.
#
# See comment at top for this job's logic.
#----------------------------------------------------------------------
class Transform:
    def __init__(self):
        self.filt   = """\
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

 <!-- Put the start and completion dates at the top of the admin info. -->
 <xsl:template                  match = 'EntryCriteria'>
  <ArmsOrGroups SingleArmOrGroupStudy='Yes'/>
  <xsl:copy>
   <xsl:apply-templates        select = '@*|node()|comment()|
                                         processing-instruction()'/>
  </xsl:copy>
 </xsl:template>

 <!-- These are being replaced. -->
 <xsl:template                  match = 'ArmsOrGroups'/>
 
</xsl:transform>
"""
    def run(self, docObj):
        docId = cdr.exNormalize(docObj.id)[1]
        if docObj.xml.find("<ArmsOrGroups") != -1:
            self.job.log("CDR%d already has ArmsOrGroups element!" % docId)
            return docObj.xml
        result  = cdr.filterDoc('guest', self.filt, doc = docObj.xml,
                                inline = True)
        if type(result) in (str, unicode):
            raise Exception(result)
        if result[0].find('SingleArmOrGroupStudy') == -1:
            self.job.log("Couldn't find anywhere to put attribute for CDR%d!" %
                         docId)
        return result[0]

#----------------------------------------------------------------------
# Collect the IDs for the documents to be modified.
#----------------------------------------------------------------------
if len(sys.argv) < 5 or sys.argv[4] not in ('test', 'live'):
    sys.stderr.write("usage: %s uid pwd xls-file test|live\n" % sys.argv[0])
    sys.exit(1)
xlsFile = sys.argv[3]
book    = ExcelReader.Workbook(xlsFile)
sheet   = book[1]
docIds  = set()
for row in sheet:
    try:
        docId = int(row[0].val)
        docIds.add(docId)
    except:
        pass
docIds = list(docIds)
docIds.sort()
sys.stderr.write("loaded %d document IDs\n" % len(docIds))
testMode        = sys.argv[4] == 'test'
filterObject    = Filter(docIds)
transformObject = Transform()
job = ModifyDocs.Job(sys.argv[1], sys.argv[2], filterObject, transformObject,
                     "Inserting SingleArmOrGroupStudy attribute.",
                     testMode = testMode)
transformObject.job = job
sys.stdout.flush()
job.run()
