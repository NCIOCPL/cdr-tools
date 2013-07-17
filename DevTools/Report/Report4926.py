#----------------------------------------------------------------------
#
# $Id$
#
# Spreadsheet of sample glossary terms for pronunciation test.
#
# BZIssue::4926
#
#----------------------------------------------------------------------
import ExcelReader, xlwt, lxml.etree as etree, cdrdb, sys, glob, time

def makeSheet(book, name):
    sheet = book.add_sheet(name)
    sheet.write(0, 0, "CDR ID")
    sheet.write(0, 1, "Term Name")
    sheet.write(0, 2, "Language")
    sheet.write(0, 3, "Pronunciation")
    sheet.write(0, 4, "Filename")
    sheet.write(0, 5, "Notes (Vanessa)")
    sheet.write(0, 6, "Approved?")
    sheet.write(0, 7, "Notes (NCI)")
    return sheet

def addDoc(sheet, doc, rowNumber):
    for name in doc.names:
        sheet.write(rowNumber, 0, doc.docId)
        sheet.write(rowNumber, 1, name.string)
        sheet.write(rowNumber, 2, name.language)
        if name.pronunciation:
            sheet.write(rowNumber, 3, name.pronunciation) 
        rowNumber += 1
    return rowNumber

def saveBook(book, name):
    fp = open(name, 'wb')
    book.save(fp)
    fp.close()

def isNewlyPublishable(docId, cursor, cutoff="2012-02-04"):
    cursor.execute("""\
SELECT MIN(dt)
  FROM doc_version
 WHERE id = ?
   AND publishable = 'Y'""", docId)
    return cursor.fetchall()[0][0] >= cutoff

class TermName:
    def __init__(self, node, language):
        self.language = language
        self.string = self.pronunciation = u""
        for child in node.findall('TermNameString'):
            self.string = child.text
        if language == 'English':
            for child in node.findall('TermPronunciation'):
                self.pronunciation = child.text

class TermNameDoc:
    def __init__(self, docId, cursor):
        self.docId = docId
        self.names = []
        cursor.execute("SELECT xml FROM document WHERE id = ?", docId)
        docXml = cursor.fetchall()[0][0]
        tree = etree.XML(docXml.encode('utf-8'))
        for nameNode in tree.findall('TermName'):
            self.names.append(TermName(nameNode, 'English'))
        for nameNode in tree.findall('TranslatedName'):
            self.names.append(TermName(nameNode, 'Spanish'))

cursor = cdrdb.connect('CdrGuest').cursor()
cursor.execute("""\
    SELECT d.id
      FROM document d
      JOIN doc_type t
        ON t.id = d.doc_type
      JOIN pub_proc_cg c
        ON c.id = d.id
     WHERE t.name = 'GlossaryTermName'""")
docIds = [row[0] for row in cursor.fetchall()]
docIds.sort()

alreadyDone = set()
names = glob.glob("SpreadsheetsForVanessa/Report4926-20*.xls")
for name in names:
    count = 0
    book = ExcelReader.Workbook(name)
    sheet = book[0]
    for row in sheet:
        try:
            alreadyDone.add(int(row[0].val))
            count += 1
        except:
            print "skipping %s" % (row[0].val)
    print "collected %d IDs from %s" % (count, name)
print "collected %d IDs for documents " % len(alreadyDone)
book = xlwt.Workbook(encoding="UTF-8")
sheet = makeSheet(book, "A")
rowNumber = 1
done = 0
added = 0
for docId in docIds:
    if docId in alreadyDone:
        continue
    try:
        doc = TermNameDoc(docId, cursor)
        if doc.names[0].pronunciation:
            rowNumber = addDoc(sheet, doc, rowNumber)
            alreadyDone.add(docId)
            added += 1
    except Exception, e:
        sys.stderr.write("\nCDR%d: %s\n" % (docId, e))
    finally:
        done += 1
        sys.stderr.write("\rprocessed %d of %d documents" %
                         (done, len(docIds)))
now = time.strftime("%Y%m%d")
name = "SpreadsheetsForVanessa/Report4926-%s.xls" % now
saveBook(book, name)
print "\nsaved %d terms in %s" % (added, name)
