#----------------------------------------------------------------------
#
# $Id$
#
# Bug 4547 -  FDAAA - Update Responsible Party with data from DCP, CTEP and
# CCRPopulate ResponsibleParty elements from spreadsheet.
#
# "This is an urgent request since there is external pressure on NCI to report
# this information:
#
# The attached spreadsheet has data from DCP that will be used to populate the
# Responsible Party element:
#
# For the protocols onthe list (use CDRID to match), update the Inscope
# Protocol records Responsible Party information.
#
# Use the CTEP Person ID to look up in the External Map table with the Usage
# type of CTSU_Person_ID. Use the mapped CDR Person ID as the ID to be used in
# the mapping for ResponsiblePerson data element. Since this is a
# personfragmentlink, I would recommend that we map to the fragment that is
# the target of the CIPSCOntact. 
#
# Use the Phone number and email address in the spreadsheet to enter the
# specific email phone and email in the protocol document ResponsibleParty
# block.
#
# I am also attaching a spreadsheet with mapping for CTEP Person IDs that were
# missing from the mapping table. You will need to update the mapping table
# first and then run the global change. I would like to see the global change
# in Test mode.
#
# FOr CCR, when we get the spreadsheet, we may not get the person ids. CIAT
# may need to provide Bob with CDR Person IDs for those person records so
# he can populate.
#
# This is the highest priority issue for CIAT also, so I expect that QA will
# be done as soon as possible."
#
# Bob, if you work on the weekend on this, please call me so I can review the
# data.
#
# BZIssue::4547
#
#----------------------------------------------------------------------
import cdr, cdrdb, re, sys, ModifyDocs, xml.dom.minidom, cgi, ExcelReader

LOGFILE = 'd:/cdr/log/Request4547.log'

class Trial:
    def __init__(self, row):
        self.cdrId = int(row[0].val)
        self.ctepPersonId = unicode(str(row[6]), 'utf-8').strip()
        self.specificPhone = unicode(str(row[9]), 'utf-8').strip()
        self.specificEmail = unicode(str(row[10]), 'utf-8').strip()
        self.personName = unicode(str(row[8]), 'utf-8').strip()

#----------------------------------------------------------------------
# The Filter class is given to the ModifyDocs.Job object, which invokes
# the getDocIds() method to retrieve a list of CDR document IDs for
# processing.
#----------------------------------------------------------------------
class Filter:
    def __init__(self, docIds):
        self.docIds = docIds
    def getDocIds(self):
        self.docIds.sort()
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
    def __init__(self, trials):
        self.trials = trials
        self.filt   = u"""\
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

 <!--
 =======================================================================
 Add ResponsibleParty to the end of the RegulatoryInformation block.
 ======================================================================= -->
 <xsl:template                  match = 'RegulatoryInformation'>
  <!-- Copy this, then add new element after it -->
  <xsl:copy>
   <xsl:apply-templates        select = '@*|node()|comment()|
                                         processing-instruction()'/>
   <ResponsibleParty>
    <ResponsiblePerson>
     <Person cdr:ref='%s'>%s</Person>
     %s
     %s
    </ResponsiblePerson>
   </ResponsibleParty>
  </xsl:copy>
 </xsl:template>

</xsl:transform>
"""
    def run(self, docObj):
        docId = cdr.exNormalize(docObj.id)[1]
        trial = self.trials[docId]
        link = u"CDR%010d#%s" % (trial.cdrPersonId, trial.cipsContactId)
        name = cgi.escape(trial.personName)
        phone = email = ""
        if trial.specificPhone:
            phone = (u"<SpecificPhone>%s</SpecificPhone>" %
                     cgi.escape(trial.specificPhone))
        if trial.specificEmail:
            email = (u"<SpecificEmail>%s</SpecificEmail>" %
                     cgi.escape(trial.specificEmail))
        filt = (self.filt % (link, name, phone, email)).encode('utf-8')
        result  = cdr.filterDoc('guest', filt, doc = docObj.xml, inline = True)
        if type(result) in (str, unicode):
            raise Exception(result)
        return result[0]

#----------------------------------------------------------------------
# Collect the data to be added to the protocol docs.
#----------------------------------------------------------------------
if len(sys.argv) < 5 or sys.argv[4] not in ('test', 'live'):
    sys.stderr.write("usage: %s uid pwd xls-file test|live\n" % sys.argv[0])
    sys.exit(1)
xlsFile = sys.argv[3]
book    = ExcelReader.Workbook(xlsFile)
sheet   = book[0]
trials  = {}
cursor  = cdrdb.connect('CdrGuest').cursor()
for row in sheet:
    try:
        trial = Trial(row)
        if not trial.ctepPersonId:
            msg = "%d has no CTEP Person ID" % trial.cdrId
            cdr.logwrite(msg, LOGFILE)
            print msg
            continue
        cursor.execute("""\
            SELECT value
              FROM query_term
             WHERE path = '/InScopeProtocol/RegulatoryInformation/FDARegulated'
               AND doc_id = ?""", trial.cdrId)
        rows = cursor.fetchall()
        if not rows:
            msg = "%d has no RegulatoryInformation block" % trial.cdrId
            cdr.logwrite(msg, LOGFILE)
            print msg
            continue
        cursor.execute("""\
            SELECT value
              FROM query_term
             WHERE path LIKE '/InScopeProtocol/RegulatoryInformation' +
                             '/ResponsibleParty/%'
               AND doc_id = ?""", trial.cdrId)
        rows = cursor.fetchall()
        if rows:
            msg = "%d already has responsible party info" % trial.cdrId
            cdr.logwrite(msg, LOGFILE)
            print msg
            continue
        cursor.execute("""\
            SELECT m.doc_id
              FROM external_map m
              JOIN external_map_usage u
                ON u.id = m.usage
             WHERE u.name = 'CTSU_Person_ID'
               AND m.value = ?
               AND m.bogus = 'N'
               AND m.doc_id IS NOT NULL
               AND m.mappable = 'Y'""", trial.ctepPersonId)
        rows = cursor.fetchall()
        if not rows:
            msg = ("CTEP person ID '%s' for %d has no match in the "
                   "mapping table" % (trial.ctepPersonId, trial.cdrId))
            cdr.logwrite(msg, LOGFILE)
            print msg
            continue
        if len(rows) > 1:
            msg = ("CTEP person ID '%s' for %d has multiple matches in the "
                   "mapping table" % (trial.ctepPersonId, trial.cdrId))
            cdr.logwrite(msg, LOGFILE)
            print msg
            continue
        trial.cdrPersonId = rows[0][0]
        cursor.execute("""\
            SELECT value
              FROM query_term
             WHERE path = '/Person/PersonLocations/CIPSContact'
               AND doc_id = ?""", trial.cdrPersonId)
        rows = cursor.fetchall()
        if not rows or not rows[0][0]:
            msg = ("can't find CIPSContact ID for person %d in trial %d" %
                   (trial.cdrPersonId, trial.cdrId))
            cdr.logwrite(msg, LOGFILE)
            print msg
            continue
        trial.cipsContactId = rows[0][0]
        trials[trial.cdrId] = trial
    except Exception, e:
        msg = "skipping '%s' (%s)" % ([str(cell) for cell in row], e)
        cdr.logwrite(msg, LOGFILE)
        print msg

sys.stderr.write("loaded %d trials\n" % len(trials))
cdr.logwrite("loaded %d trials" % len(trials), LOGFILE)
testMode        = sys.argv[4] == 'test'
cdr.logwrite("running in %s mode" % sys.argv[4], LOGFILE)
filterObject    = Filter(trials.keys())
transformObject = Transform(trials)
job = ModifyDocs.Job(sys.argv[1], sys.argv[2], filterObject, transformObject,
                     "Adding ResponsibleParty (request #4547).",
                     testMode = testMode, logFile = LOGFILE, validate = True)
sys.stdout.flush()
job.run()
