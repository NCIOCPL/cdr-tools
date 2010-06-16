#----------------------------------------------------------------------
#
# $Id$
#
# Imports SummaryDescription and SummaryURL elements into Summary
# documents.
#
# "We added two new required elements to the summary schema. We need to import 
# the data for these elements from the file. Until then summary documents on 
# MAHLER will become invalid when you open them on MAHLER. I noticed that the 
# file that Olga sent us did not have CDRIDs and I have asked if she can
# provide them to us so we can programmatically map it.
#
# "For each CDRID, please import the Description and URL columns into Summary
# documents for the following elements 
#
#   SummaryDescription
#   SummaryURL (cdr:xref attribute)
#
# BZIssue::1663
#
#----------------------------------------------------------------------
import cdr, cdrdb, re, sys, ModifyDocs, xml.sax.saxutils, ExcelReader

entities = {}
pattern  = re.compile("&[^;]+;")
def checkTitle(title):
    matches = pattern.findall(title)
    if matches:
        for match in matches:
            entities[match] = entities.get(match, 0) + 1

def getAlreadyDone():
    conn = cdrdb.connect('CdrGuest')
    cursor = conn.cursor()
    cursor.execute("""\
SELECT DISTINCT doc_id
           FROM query_term
          WHERE path = '/Summary/SummaryMetaData/SummaryURL/@cdr:xref'""")
    ids = {}
    for row in cursor.fetchall():
        ids[row[0]] = True
    return ids

#----------------------------------------------------------------------
# Collects needed values for summary documents.
#----------------------------------------------------------------------
class Doc:
    def __init__(self, cdrId, title, desc, url, rowNumber):
        self.cdrId     = cdrId and int(cdrId.val) or None
        self.title     = title and title.val or ""
        self.desc      = desc and desc.val or ""
        self.url       = url and url.val or ""
        self.rowNumber = rowNumber
        if not self.title:
            sys.stderr.write("%s (row %d) has no title\n" % (self.cdrId,
                                                             rowNumber))
        else:
            self.title = Doc.__fix(self.title)
            checkTitle(self.title)
        if not self.url:
            sys.stderr.write("%s (row %d) has no url\n" % (self.cdrId,
                                                           rowNumber))
    def __fix(title):
        return (title.replace("&eacute;", u"\u00e9")
                     .replace("&ntilde;", u"\u00f1")
                     .replace("&aacute;", u"\u00e1")
                     .replace("&reg;",    u"\u00ae")
                     .replace("&oacute;", u"\u00f3")
                     .replace("&iacute;", u"\u00ed")
                     .replace("&uacute;", u"\u00fa"))
    __fix = staticmethod(__fix)

#----------------------------------------------------------------------
# The Filter class is given to the ModifyDocs.Job object, which invokes
# the getDocIds() method to retrieve a list of CDR document IDs for
# processing.
#----------------------------------------------------------------------
class Filter:
    def __init__(self, docs):
        self.ids = docs.keys()
        self.ids.sort()
    def getDocIds(self):
        sys.stderr.write("%s\n" % self.ids[0:2])
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
    def __init__(self, docs):
        self.docs = docs
    def run(self, docObj):
        docIds = cdr.exNormalize(docObj.id)
        docId  = docIds[1]
        doc    = self.docs[docId]
        filt   = u"""\
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

 <!-- Skip these guys; we'll insert out own. -->
 <xsl:template                  match = 'SummaryDescription | SummaryURL'/>
 
 <!-- Insert new elements. -->
 <xsl:template                  match = 'SummaryLanguage'>
  <xsl:copy>
   <xsl:apply-templates        select = '@*|node()|comment()|
                                         processing-instruction()'/>
  </xsl:copy>
  <SummaryDescription>%s</SummaryDescription>
  <SummaryURL                cdr:xref = %s>%s</SummaryURL>
 </xsl:template>
</xsl:transform>
""" % (xml.sax.saxutils.escape(doc.desc),
       xml.sax.saxutils.quoteattr(u"http://cancer.gov" + doc.url),
       xml.sax.saxutils.escape(doc.title))
        if type(filt) == type(u""):
            filt = filt.encode('utf-8')
        result = cdr.filterDoc('guest', filt, doc = docObj.xml, inline = 1)
        if type(result) in (type(""), type(u"")):
            raise Exception(result)
        return result[0]

#----------------------------------------------------------------------
# Collect the data to be added to the Summary docs.
#----------------------------------------------------------------------
if len(sys.argv) < 5 or sys.argv[4] not in ('test', 'live'):
    sys.stderr.write("usage: Request1663.py uid pwd workbook test|live\n")
    sys.exit(1)
bookName = sys.argv[3]
workbook = ExcelReader.Workbook(bookName)
sheet    = workbook[0]
docs     = {}
doneIds  = [] #getAlreadyDone()
for row in sheet:
    if row.number > 0: # skip header row
        cdrId = row[0]
        title = row[1]
        desc  = row[2]
        url   = row[3]
        doc   = Doc(cdrId, title, desc, url, row.number + 1)
        if doc.cdrId in docs:
            sys.stderr.write("duplicate %d on rows %d and %d\n",
                             doc.cdrId, docs[doc.cdrId].rowNumber,
                             row.number + 1)
        elif doc.cdrId in doneIds:
            sys.stderr.write("skipping %s -- already done\n" % doc.cdrId)
        else:
            docs[doc.cdrId] = doc
sys.stderr.write("loaded %d docs\n" % len(docs))
for entity in entities:
    print "%5d: %s" % (entities[entity], entity)
testMode        = sys.argv[4] == 'test'
filterObject    = Filter(docs)
transformObject = Transform(docs)
job = ModifyDocs.Job(sys.argv[1], sys.argv[2], filterObject, transformObject,
                     "Adding CG Summary elements (request #1663).",
                     testMode = testMode)
sys.stdout.flush()
job.run()
