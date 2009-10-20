#----------------------------------------------------------------------
#
# $Id$
#
# Modifies trial dates.
#
# "We need to create a web site similar to what was done for the Outcomes
# project to collect Completion Date. Bob and I discussed some ideas for how
# to do this and he was going to mock something up. I might ask for a quick
# consult with someone from Marcus' team on Monday. This needs to get done as
# soon as possible so that an email with a link can go out by the end of next
# week."
#
# This global change script is the data import piece which pulls the
# information collected by the web interface described above into the CDR.
#
# BZIssue::3757
# BZIssue::3781
#
#----------------------------------------------------------------------
import cdr, cdrdb, re, sys, ModifyDocs, xml.dom.minidom, cgi

#----------------------------------------------------------------------
# Object holding trial date information.
#----------------------------------------------------------------------
class Trial:
    def __init__(self, node):
        self.docId = int(node.getAttribute('docId'))
        self.sDate = node.getAttribute('sdate')
        self.sType = node.getAttribute('stype')
        self.cDate = node.getAttribute('cdate')
        self.cType = node.getAttribute('ctype')

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

 <xsl:param                      name = 'sDate' />
 <xsl:param                      name = 'sType' />
 <xsl:param                      name = 'cDate' />
 <xsl:param                      name = 'cType' />
 
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
   <xsl:if                       test = 'concat($sDate, $sType) != ""'>
    <StartDate>
    <xsl:attribute               name = 'DateType'>
     <xsl:value-of             select = '$sType'/>
    </xsl:attribute>
     <xsl:value-of             select = '$sDate'/>
    </StartDate>
   </xsl:if>
   <xsl:if                       test = 'concat($cDate, $cType) != ""'>
    <CompletionDate>
    <xsl:attribute               name = 'DateType'>
     <xsl:value-of             select = '$cType'/>
    </xsl:attribute>
     <xsl:value-of             select = '$cDate'/>
    </CompletionDate>
   </xsl:if>
   <xsl:apply-templates        select = '@*|node()|comment()|
                                         processing-instruction()'/>
  </ProtocolAdminInfo>
 </xsl:template>

 <!-- These are being replaced. -->
 <xsl:template                  match = 'ProtocolAdminInfo/StartDate|
                                         ProtocolAdminInfo/CompletionDate'/>
 
</xsl:transform>
"""
    def run(self, docObj):
        docId = cdr.exNormalize(docObj.id)[1]
        trial = self.trials[docId]
        sDate = ('sDate', trial.sDate)
        sType = ('sType', mapDateType(trial.sType))
        cDate = ('cDate', trial.cDate)
        cType = ('cType', mapDateType(trial.cType))
        parms   = (sDate, sType, cDate, cType)
        result  = cdr.filterDoc('guest', self.filt, doc = docObj.xml,
                                inline = True, parm = parms)
        if type(result) in (str, unicode):
            raise Exception(result)
        return result[0]

def mapDateType(t):
    if t == 'A':
        return 'Actual'
    if t == 'P':
        return 'Projected'
    return ''

#----------------------------------------------------------------------
# Collect the data to be added to the protocol docs.
#----------------------------------------------------------------------
if len(sys.argv) < 5 or sys.argv[4] not in ('test', 'live'):
    sys.stderr.write("usage: Request3757.py uid pwd xml-file test|live\n")
    sys.exit(1)
xmlFile = sys.argv[3]
dom     = xml.dom.minidom.parse(xmlFile)
trials  = {}
for node in dom.documentElement.childNodes:
    if node.nodeName == 'Trial':
        trial = Trial(node)
        trials[trial.docId] = trial
sys.stderr.write("loaded %d trials\n" % len(trials))
testMode        = sys.argv[4] == 'test'
filterObject    = Filter(trials)
transformObject = Transform(trials)
job = ModifyDocs.Job(sys.argv[1], sys.argv[2], filterObject, transformObject,
                     "Modifying trial dates (requests #3757 and #3781).",
                     testMode = testMode)
sys.stdout.flush()
job.run()
