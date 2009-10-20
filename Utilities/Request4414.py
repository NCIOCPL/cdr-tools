#----------------------------------------------------------------------
#
# $Id$
#
# Populate CTGovInterventionType elements from spreadsheet.
#
# "We recently added a new element in Term documents <CTGovInterventionType>
# that we will be using for CTGov mapping and a global was performed (issue
# 4351) to map the <CTGovInterventionType> element to Term documents
# with <SemanticType> of "Intervention or procedure".
#
# We now will need to map the <CTGovInterventionType> element to Term documents
# with <SemanticType> of "Drug/agent".  We are compiling a spreadsheet that
# lists the CDR ID of each term with the corresponding <CTGovInterventionType>
# value.
#
# A version should be made of the Term document according to the last version
# made.
#
# The first attachment is a spreadsheet that has 1643 terms with the
# appropriate mapping.  We can use this for testing purposes, if needed, while
# CIAT is reviewing 900 more terms to add to the mapping spreadsheet. The
# mapping for the 900 terms should hopefully be finished by next week."
#
# BZIssue::4414
#
#----------------------------------------------------------------------
import cdr, cdrdb, re, sys, ModifyDocs, xml.dom.minidom, cgi, ExcelReader

LOGFILE = 'd:/cdr/log/Request4414.log'

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

 <!--
 =======================================================================
 We've already determined that there is only one of these in the
 document.  Copy it and then pop in the CTGovInterventionType element.
 ======================================================================= -->
 <xsl:template                  match = 'SemanticType'>
  <!-- Copy this, then add new element after it -->
  <xsl:copy>
   <xsl:apply-templates        select = '@*|node()|comment()|
                                         processing-instruction()'/>
  </xsl:copy>
  <CTGovInterventionType>%s</CTGovInterventionType>
 </xsl:template>

</xsl:transform>
"""
    def run(self, docObj):
        docId = cdr.exNormalize(docObj.id)[1]
        filt  = self.filt % self.trials[docId]
        result  = cdr.filterDoc('guest', filt, doc = docObj.xml, inline = True)
        if type(result) in (str, unicode):
            raise Exception(result)
        return result[0]

#----------------------------------------------------------------------
# Collect the data to be added to the protocol docs.
#----------------------------------------------------------------------
if len(sys.argv) < 5 or sys.argv[4] not in ('test', 'live'):
    sys.stderr.write("usage: Request4414.py uid pwd xls-file test|live\n")
    sys.exit(1)
xlsFile = sys.argv[3]
book    = ExcelReader.Workbook(xlsFile)
sheet   = book[0]
terms   = {}
cursor  = cdrdb.connect('CdrGuest').cursor()
for row in sheet:
    try:
        docId = int(row[0].val)
        itype = row[2].val.encode('utf-8')
        cursor.execute("""\
            SELECT value
              FROM query_term
             WHERE path = '/Term/CTGovInterventionType'
               AND doc_id = ?""", docId)
        rows = cursor.fetchall()
        for row in rows:
            msg = "%d already has CT.gov intervention type '%s'" % (docId,
                                                                    row[0])
            cdr.logwrite(msg, LOGFILE)
            print msg
        if rows:
            continue
        cursor.execute("""\
            SELECT value
              FROM query_term
             WHERE path = '/Term/SemanticType/@cdr:ref'
               AND doc_id = ?""", docId)
        rows = cursor.fetchall()
        if len(rows) != 1:
            msg = "%d has %d semantic type links" % (docId, len(rows))
            cdr.logwrite(msg, LOGFILE)
            for row in rows:
                cdr.logwrite(row[0], LOGFILE)
                print "\t%s" % row[0]
        else:
            terms[docId] = itype
    except:
        pass
sys.stderr.write("loaded %d terms\n" % len(terms))
cdr.logwrite("loaded %d terms" % len(terms), LOGFILE)
testMode        = sys.argv[4] == 'test'
cdr.logwrite("running in %s mode" % sys.argv[4], LOGFILE)
filterObject    = Filter(terms.keys())
transformObject = Transform(terms)
job = ModifyDocs.Job(sys.argv[1], sys.argv[2], filterObject, transformObject,
                     "Adding CTGovInterventionType (request #4414).",
                     testMode = testMode, logFile = LOGFILE)
sys.stdout.flush()
job.run()
