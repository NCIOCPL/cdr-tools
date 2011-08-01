#----------------------------------------------------------------------
#
# $Id$
#
# Populate new NCIThesaurusConcept element.
#
# BZIssue::4984
#
#----------------------------------------------------------------------
import ModifyDocs, sys, lxml.etree as etree, cdr, cdrdb, ExcelReader, re

class Request4984:
    def __init__(self, docs):
        self.docs = docs
    def getDocIds(self):
        docIds = docs.keys()
        docIds.sort()
        return [docId for docId in docIds if self.docs[docId].newConcepts]
    def run(self, docObject):
        docId = cdr.exNormalize(docObject.id)[1]
        doc = self.docs[docId]
        tree = etree.XML(docObject.xml)
        if tree.findall('NCIThesaurusConcept'):
            return docObject.xml

        # This slightly ugly bit of logic is needed to determine where
        # the newly inserted elements go, because for some reason the
        # schema allows Comment elements in two different places at the
        # top level!
        position = 0
        termStatusSeen = False
        for node in tree:
            if termStatusSeen and node.tag != 'MenuInformation':
                break
            position += 1
            if node.tag == 'TermStatus':
                termStatusSeen = True
        for conceptId in doc.newConcepts:
            if not re.match("C\\d+", conceptId):
                sys.stderr.write("CDR%d: funky concept ID: '%s'\n" %
                                 (docId, conceptId))
            child = etree.Element('NCIThesaurusConcept')
            child.text = conceptId
            tree.insert(position, child)
            position += 1
        return etree.tostring(tree)

class Doc:
    def __init__(self, docId):
        self.docId = docId
        self.oldConcepts = set()
        self.newConcepts = set()

if len(sys.argv) != 4 or sys.argv[3] not in ('test', 'live'):
    sys.stderr.write("usage: %s uid pwd test|live\n" % sys.argv[0])
    sys.exit(1)
uid, pwd, flag = sys.argv[1:]
testMode = flag == 'test'
cursor = cdrdb.connect('CdrGuest').cursor()
docs = {}
cursor.execute("""\
SELECT doc_id, value
  FROM query_term
 WHERE path = '/Term/NCIThesaurusConcept'""")
for docId, conceptId in cursor.fetchall():
    doc = docs.get(docId)
    if not doc:
        doc = docs[docId] = Doc(docId)
    doc.oldConcepts.add(conceptId)
cursor.execute("""\
SELECT i.doc_id, i.value
  FROM query_term i
  JOIN query_term s
    ON s.doc_id = i.doc_id
   AND LEFT(s.node_loc, 8) = LEFT(i.node_loc, 8)
 WHERE s.path = '/Term/OtherName/SourceInformation/VocabularySource/SourceCode'
   AND s.value = 'NCI Thesaurus'
   AND i.path = '/Term/OtherName/SourceInformation/VocabularySource'
              + '/SourceTermId'""")
for docId, conceptId in cursor.fetchall():
    doc = docs.get(docId)
    if not doc:
        doc = docs[docId] = Doc(docId)
    if conceptId not in doc.oldConcepts:
        doc.newConcepts.add(conceptId)
book = ExcelReader.Workbook(r'\\franck\d$\tmp\task4984.xls')
sheet = book[0]
for row in sheet:
    try:
        cdrId = row[8].val
        intId = cdr.exNormalize(cdrId)[1]
    except Exception, e:
        sys.stderr.write("%s: %s\n" % (cdrId, e))
        continue
    conceptId = row[16].val
    doc = docs.get(intId)
    if not doc:
        doc = docs[intId] = Doc(intId)
    if conceptId not in doc.oldConcepts:
        doc.newConcepts.add(conceptId)

obj = Request4984(docs)
job = ModifyDocs.Job(uid, pwd, obj, obj,
                     "Populate NCIThesaurusConcept element (BZIssue::4984)",
                     validate=True, testMode=testMode)
job.run()
