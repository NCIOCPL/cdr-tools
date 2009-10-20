#----------------------------------------------------------------------
#
# $Id$
#
# Global insert of Completion dates from CTEP (request #3797).
#
# "We need to globally insert Completion dates given from CTEP into
# InScopeProtocols.  I will attach a spreadsheet which highlights the CDR ID
# and Completion date column to use.
#
# The <CompletionDate> that is inserted into the CDR should have an attribute
# of 'Projected'."
#
# BZIssue::3797
#
#----------------------------------------------------------------------
import cdr, cdrdb, re, sys, ModifyDocs, xml.dom.minidom, cgi, ExcelReader

#----------------------------------------------------------------------
# The Filter class is given to the ModifyDocs.Job object, which invokes
# the getDocIds() method to retrieve a list of CDR document IDs for
# processing.
#----------------------------------------------------------------------
class Filter:
    def __init__(self, trials):
        self.trials = trials
    def getDocIds(self):
        docIds = self.trials.keys()
        docIds.sort()
        return docIds

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
 <xsl:template                  match = 'ProtocolAdminInfo'>
  <ProtocolAdminInfo>
   <xsl:for-each               select = 'StartDate'>
    <xsl:copy>
     <xsl:apply-templates     select = '@*|node()|comment()|
                                         processing-instruction()'/>
    </xsl:copy>
   </xsl:for-each>
   <CompletionDate DateType='Projected'>%s</CompletionDate>
   <xsl:apply-templates        select = '@*|node()|comment()|
                                         processing-instruction()'/>
  </ProtocolAdminInfo>
 </xsl:template>

 <!-- These are being replaced or inserted manually. -->
 <xsl:template                  match = 'ProtocolAdminInfo/StartDate|
                                         ProtocolAdminInfo/CompletionDate'/>
 
</xsl:transform>
"""
    def run(self, docObj):
        docId = cdr.exNormalize(docObj.id)[1]
        cdate = self.trials[docId].encode('ascii')
        filt  = self.filt % cdate
        result  = cdr.filterDoc('guest', self.filt % cdate, doc = docObj.xml,
                                inline = True)
        if type(result) in (str, unicode):
            raise Exception(result)
        return result[0]

#----------------------------------------------------------------------
# Collect the data to be added to the protocol docs.
#----------------------------------------------------------------------
if len(sys.argv) < 5 or sys.argv[4] not in ('test', 'live'):
    sys.stderr.write("usage: Request3797.py uid pwd xls-file test|live\n")
    sys.exit(1)
xlsFile = sys.argv[3]
book    = ExcelReader.Workbook(xlsFile)
sheet   = book[0]
trials  = {}
for row in sheet:
    try:
        docId = int(row[0].val)
        cdate = row[4].format()
        trials[docId] = cdate[:10]
    except:
        pass
sys.stderr.write("loaded %d trials\n" % len(trials))
testMode        = sys.argv[4] == 'test'
filterObject    = Filter(trials)
transformObject = Transform(trials)
job = ModifyDocs.Job(sys.argv[1], sys.argv[2], filterObject, transformObject,
                     "Modifying CTEP trial dates (request #3797).",
                     testMode = testMode)
sys.stdout.flush()
job.run()
