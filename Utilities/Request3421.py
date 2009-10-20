#----------------------------------------------------------------------
#
# $Id$
#
# Modifies summary titles.
#
# "We are working with Cancer.gov to have them take the PDQ summary titles and
# short titles directly from the CDR data.  They currently only use the summary
# titles for new summaries, and the short titles are not stored in the CDR at
# all.  Updates to all titles have to be made in the Cancer.gov admin system
# directly.  
#
# They also manipulate the titles by adding the (PDQ trademark), and in some
# cases, a colon followed by the type of summary (e.g., :Treatment.  We are
# changing the summary titles so that this will not be necessary.  The only
# thing that will need to be added to the titles during publishing will be the
# (PDQ trademark).

# I am attaching a spreadsheet that contains the CDRID(A), current title in the
# Cancer.gov admin system(B), the new complete PDQ summary title(C), and the
# short title (D).

# After the new Gatekeeper is in place, we would like to populate the
# SummaryTitle and the AltTitle from the spreadsheet.  The SummaryTitle would
# come from column C, and the AltTitle would come from column D.  (I thought we
# had put in a TitleType attribute on the AltTitle to describe it as a short or
# brief title, but I don't see it in the schema--maybe I am looking in the 
# wrong place.)

# We have a meeting scheduled with Cancer.gov this week to go over the entire
# process for making the title change, but I wanted to get the issue in with 
# the spreadsheet."
#
# BZIssue::3421
#
#----------------------------------------------------------------------
import cdr, cdrdb, re, sys, ModifyDocs, ExcelReader, cgi

#----------------------------------------------------------------------
# Object holding summary title information.
#----------------------------------------------------------------------
class Summary:
    def __init__(self, row):
        self.docId = int(row[0].val)
        self.viewTitle = row[1].val
        self.newPdqTitle = row[2].val
        self.viewShortTitle = row[3].val

#----------------------------------------------------------------------
# The Filter class is given to the ModifyDocs.Job object, which invokes
# the getDocIds() method to retrieve a list of CDR document IDs for
# processing.
#----------------------------------------------------------------------
class Filter:
    def __init__(self, summaries):
        self.summaries = summaries
    def getDocIds(self):
        docIds = self.summaries.keys()
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
    def __init__(self, summaries):
        self.summaries = summaries
        self.filt      = """\
<?xml version='1.0' encoding='UTF-8'?>

<xsl:transform                version = '1.0' 
                            xmlns:xsl = 'http://www.w3.org/1999/XSL/Transform'
                            xmlns:cdr = 'cips.nci.nih.gov/cdr'>

 <xsl:output                   method = 'xml'/>

 <xsl:param                      name = 'title' />
 <xsl:param                      name = 'shortTitle' />
 
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

 <!-- Replace SummaryTitle and insert short title if missing. -->
 <xsl:template                  match = 'Summary/SummaryTitle'>
  <SummaryTitle>
   <xsl:value-of               select = '$title'/>
  </SummaryTitle>
  <xsl:if                        test = 'not(../AltTitle[@TitleType="Short"])'>
   <AltTitle                TitleType = 'Short'>
    <xsl:value-of              select = '$shortTitle'/>
   </AltTitle>
  </xsl:if>
 </xsl:template>

 <!-- Replace short title if the document already has it. -->
 <xsl:template                  match = '/Summary/AltTitle[@TitleType="Short"]'>
  <AltTitle                 TitleType = 'Short'>
   <xsl:value-of               select = '$shortTitle'/>
  </AltTitle>
 </xsl:template>
 
</xsl:transform>
"""
    def run(self, docObj):
        docIds  = cdr.exNormalize(docObj.id)
        docId   = docIds[1]
        summary = self.summaries[docId]
        title   = ('title', summary.newPdqTitle.encode('utf-8'))
        short   = ('shortTitle', summary.viewShortTitle.encode('utf-8'))
        parms   = (title, short)
        result  = cdr.filterDoc('guest', self.filt, doc = docObj.xml,
                                inline = True, parm = parms)
        if type(result) in (str, unicode):
            raise Exception(result)
        return result[0]

#----------------------------------------------------------------------
# Collect the data to be added to the Summary docs.
#----------------------------------------------------------------------
if len(sys.argv) < 5 or sys.argv[4] not in ('test', 'live'):
    sys.stderr.write("usage: Request3421.py uid pwd workbook test|live\n")
    sys.exit(1)
bookName  = sys.argv[3]
workbook  = ExcelReader.Workbook(bookName)
sheet     = workbook[0]
summaries = {}
for row in sheet:
    try:
        summary = Summary(row)
        summaries[summary.docId] = summary
    except:
        pass
sys.stderr.write("loaded %d summaries\n" % len(summaries))
testMode        = sys.argv[4] == 'test'
filterObject    = Filter(summaries)
transformObject = Transform(summaries)
job = ModifyDocs.Job(sys.argv[1], sys.argv[2], filterObject, transformObject,
                     "Modifying summary titles (request #3421).",
                     testMode = testMode)
sys.stdout.flush()
job.run()
