#----------------------------------------------------------------------
#
# $Id$
#
# Imports gender information into protocol documents.
#
# BZIssue::2713
#
#----------------------------------------------------------------------
import cdr, cdrdb, re, sys, ModifyDocs, ExcelReader, cgi

def fix(me):
    if not me:
        return u""
    return cgi.escape(me)

class Protocol:
    def __init__(self, docId, cursor):
        self.docId = docId
        self.profTitle = self.getTitle('Professional', cursor)
        self.origTitle = self.getTitle('Original', cursor)
    def getTitle(self, titleType, cursor):
        cursor.execute("""\
            SELECT t.value
              FROM query_term t
              JOIN query_term w
                ON t.doc_id = w.doc_id
               AND LEFT(t.node_loc, 4) = LEFT(w.node_loc, 4)
             WHERE t.path = '/InScopeProtocol/ProtocolTitle'
               AND w.path = '/InScopeProtocol/ProtocolTitle/@Type'
               AND w.value = ?
               AND t.doc_id = ?""", (titleType, self.docId))
        for rows in cursor.fetchall():
            return rows[0]
        
    def addRow(self, html):
        html.append(u"""\
   <tr>
    <td>%d</td>
    <td>%s</td>
    <td>%s</td>
   </tr>
""" % (self.docId, fix(self.profTitle), fix(self.origTitle)))
        
#----------------------------------------------------------------------
# The Filter class is given to the ModifyDocs.Job object, which invokes
# the getDocIds() method to retrieve a list of CDR document IDs for
# processing.
#----------------------------------------------------------------------
class Filter:
    def __init__(self, genders):
        self.ids = genders.keys()
        cursor = cdrdb.connect('CdrGuest').cursor()
        cursor.execute("""\
            SELECT DISTINCT doc_id
              FROM query_term
             WHERE path = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
               AND value = 'ClinicalTrials.gov ID'""")
        html = [u"""\
<html>
 <head>
  <title>InScopeProtocol Documents Not on Spreadsheet</title>
  <style type='text/css'>
   body { font-family: Arial; }
   h1   { font-size: 14pt; color: maroon }
   th   { font-size: 10pt; color: navy; }
   td   { font-size: 10pt; vertical-align: top; }
  </style>
 </head>
 <body>
  <h1>InScopeProtocols With Gender Set to 'Both'</h1>
  <table border='1' cellpadding='2' cellspacing='0'>
   <tr>
    <th>CDR ID</th>
    <th>Professional Title</th>
    <th>Original Title</th>
   </tr>
"""]
        for row in cursor.fetchall():
            if row[0] not in genders:
                self.ids.append(row[0])
                prot = Protocol(row[0], cursor)
                prot.addRow(html)
        html.append(u"""\
  </table>
 </body>
</html>
""")
        fp = open("Request2713-live-bach.html", "w")
        fp.write(u"".join(html).encode('utf-8'))
        fp.close()
        self.ids.sort()
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
    def __init__(self, genders):
        self.genders = genders
    def run(self, docObj):
        docIds = cdr.exNormalize(docObj.id)
        docId  = docIds[1]
        if docId in genders :
            gender = genders[docId] == 'M' and "Male" or "Female"
        else:
            gender = "Both"
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
 <xsl:template                  match = 'Eligibility/AgeText'>
  <xsl:copy>
   <xsl:apply-templates        select = '@*|node()|comment()|
                                         processing-instruction()'/>
  </xsl:copy>
  <Gender>%s</Gender>
 </xsl:template>
</xsl:transform>
""" % gender
        result = cdr.filterDoc('guest', filt, doc = docObj.xml, inline = True)
        if type(result) in (str, unicode):
            raise Exception(result)
        return result[0]

#----------------------------------------------------------------------
# Collect the data to be added to the Summary docs.
#----------------------------------------------------------------------
if len(sys.argv) < 5 or sys.argv[4] not in ('test', 'live'):
    sys.stderr.write("usage: Request2713.py uid pwd workbook test|live\n")
    sys.exit(1)
bookName = sys.argv[3]
workbook = ExcelReader.Workbook(bookName)
sheet    = workbook[0]
genders  = {}
for row in sheet:
    if row.number > 0: # skip header row
        cdrId  = int(row[0].val)
        gender = str(row[1].val).upper()
        if cdrId in genders:
            sys.stderr.write("duplicate %d on row %d" % (cdrId,
                                                         row.number + 1))
        elif gender in ("M", "F"):
            genders[cdrId] = gender
sys.stderr.write("loaded %d genders\n" % len(genders))
testMode        = sys.argv[4] == 'test'
filterObject    = Filter(genders)
transformObject = Transform(genders)
job = ModifyDocs.Job(sys.argv[1], sys.argv[2], filterObject, transformObject,
                     "Adding Gender element (request #2713).",
                     testMode = testMode)
sys.stdout.flush()
job.run()
