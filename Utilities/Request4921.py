#----------------------------------------------------------------------
#
# $Id$
#
# BZIssue::4921
#
#----------------------------------------------------------------------
import ExcelReader, cdrdb, ModifyDocs, lxml.etree as etree, cdr, sys

def get(row, i):
    try:
        val = row[i].val
        if val == 'NULL':
            return None
        return val
    except:
        return None

def makeChildElement(tag, attrName, attrValue, text, useWith=None):
    child = etree.Element(tag)
    child.text = text
    child.set("{cips.nci.nih.gov/cdr}%s" % attrName, attrValue)
    if useWith:
        child.set("UseWith", useWith)
    return child

def findPosition(tree):
    position = 0
    seenTermTypes = False
    for child in tree:
        if child.tag == 'TermType':
            seenTermTypes = True
        elif seenTermTypes:
            return position
        position += 1
    return position

class Concept:
    def __init__(self, row):
        self.cdrId = int(get(row, 0))
        self.termName = get(row, 1)
        self.title = get(row, 2)
        self.spanishTitle = get(row, 3)
        self.summaryId = get(row, 5)
        self.summaryTitle = get(row, 6)
        self.drugId = get(row, 8)
        self.drugTitle = get(row, 9)
        self.externalUrl = get(row, 10)
        self.spanishUrl = get(row, 11)
        if self.summaryId:
            self.summaryId = int(self.summaryId)
        if self.drugId:
            self.drugId = int(self.drugId)
    def wanted(self):
        return (self.externalUrl or self.summaryId or self.drugId or
                self.spanishUrl)
    def makeRelatedInfoElement(self):
        info = etree.Element("RelatedInformation")
        if self.externalUrl:
            child = makeChildElement("RelatedExternalRef", "xref",
                                     self.externalUrl, self.title, "en")
            info.append(child)
            #spanishUrl = spanishUrls.get(self.externalUrl)
            #if spanishUrl:
            #    child = makeChildElement("RelatedExternalRef", "xref",
            #                             spanishUrl, self.title, "es")
            #    info.append(child)
        if self.spanishUrl:
            child = makeChildElement("RelatedExternalRef", "xref",
                                     self.spanishUrl, self.spanishTitle, "es")
            info.append(child)
        if self.summaryId:
            ref = "CDR%010d" % self.summaryId
            title = self.summaryTitle or u""
            child = makeChildElement("RelatedSummaryRef", "ref", ref, title,
                                     "en")
            info.append(child)
            spanishId, title = spanishSummaries.get(self.summaryId, (None,
                                                                     None))
            if spanishId:
                ref = "CDR%010d" % spanishId
                child = makeChildElement("RelatedSummaryRef", "ref", ref,
                                         title, "es")
                info.append(child)
        if self.drugId:
            ref = "CDR%010d" % self.drugId
            title = self.drugTitle or u""
            child = makeChildElement("RelatedDrugSummaryLink", "ref", ref,
                                     title)
            info.append(child)
        return info

class Request4921:
    def __init__(self, concepts):
        self.concepts = concepts
    def getDocIds(self):
        docIds = self.concepts.keys()
        docIds.sort()
        return docIds
    def run(self, docObject):
        cdrId  = cdr.exNormalize(docObject.id)[1]
        concept = self.concepts[cdrId]
        docXml = docObject.xml
        tree = etree.XML(docXml)
        tree.insert(findPosition(tree), concept.makeRelatedInfoElement())
        return etree.tostring(tree)

if len(sys.argv) != 4 or sys.argv[3] not in ('test', 'live'):
    sys.stderr.write("usage: %s uid pwd test|live\n" % sys.argv[0])
    sys.exit(1)
uid, pwd, flag = sys.argv[1:]
testMode = flag == 'test'
cursor = cdrdb.connect('CdrGuest').cursor()
spanishSummaries = {}
cursor.execute("""\
SELECT q.doc_id, q.int_val, a.title
  FROM query_term q
  JOIN active_doc a
    ON a.id = q.doc_id
 WHERE path = '/Summary/TranslationOf/@cdr:ref'""")
for spanishId, englishId, title in cursor.fetchall():
    spanishSummaries[englishId] = (spanishId, title)
book = ExcelReader.Workbook(r"\\franck\d$\tmp\glossary-links.xls")
sheet = book[0]
concepts = {}
for row in sheet:
    try:
        concept = Concept(row)
        cdrId = concept.cdrId
    except:
        print "skipping", row[0].val
        continue
    cursor.execute("SELECT xml FROM document WHERE id = ?", cdrId)
    docXml = cursor.fetchall()[0][0]
    tree = etree.XML(docXml.encode('utf-8'))
    relatedInformation = tree.findall('RelatedInformation')
    if not tree.findall('TermType'):
        print "*** SKIPPING CDR%d: NO TERM TYPES ***" % cdrId
        continue
    if tree.findall('RelatedInformation'):
        print "*** SKIPPING CDR%d: ALREADY HAS RELATEDINFORMATION ***" % cdrId
        continue
    if concept.wanted():
        concepts[concept.cdrId] = concept
    else:
        print "*** SKIPPING CDR%d: NO RELATED INFORMATION ***" % cdrId
obj = Request4921(concepts)
job = ModifyDocs.Job(uid, pwd, obj, obj, "Request 4921", validate=True,
                     testMode=testMode)
job.run()
