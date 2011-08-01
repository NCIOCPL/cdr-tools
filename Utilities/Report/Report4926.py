#----------------------------------------------------------------------
#
# $Id$
#
# Spreadsheet of sample glossary terms for pronunciation test.
#
# BZIssue::4926
#
#----------------------------------------------------------------------
import ExcelReader, ExcelWriter, lxml.etree as etree, cdrdb, sys

def makeBook(name):
    book = ExcelWriter.Workbook()
    sheet = book.addWorksheet(name)
    row = sheet.addRow(1)
    row.addCell(1, "CDR ID")
    row.addCell(2, "Term Name")
    row.addCell(3, "Language")
    row.addCell(4, "Pronunciation")
    row.addCell(5, "Filename")
    row.addCell(6, "Notes (Vanessa)")
    row.addCell(7, "Approved?")
    row.addCell(8, "Notes (NCI)")
    return book

def addDoc(sheet, doc, rowNumber):
    for name in doc.names:
        row = sheet.addRow(rowNumber)
        rowNumber += 1
        row.addCell(1, doc.docId)
        row.addCell(2, name.string)
        row.addCell(3, name.language)
        if name.pronunciation:
            row.addCell(4, name.pronunciation)
    return rowNumber

def saveBook(book, name):
    fp = open(name, 'wb')
    book.write(fp, True)
    fp.close()

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
if len(sys.argv) > 1:
    book = ExcelReader.Workbook(sys.argv[1])
    sheet = book[0]
    for row in sheet:
        try:
            alreadyDone.add(int(row[0].val))
        except:
            print "skipping %s" % (row[0].val)
    print "collected %d IDs for documents already done" % len(alreadyDone)
books = [makeBook("B"), makeBook("A")]
sheets = [book.sheets[0] for book in books]
rowNumbers = [2, 2]
done = 0
for docId in docIds:
    if docId in alreadyDone:
        continue
    try:
        doc = TermNameDoc(docId, cursor)
        which = doc.names[0].pronunciation and 1 or 0
        rowNumbers[which] = addDoc(sheets[which], doc, rowNumbers[which])
    except Exception, e:
        sys.stderr.write("\nCDR%d: %s\n" % (docId, e))
    finally:
        done += 1
        sys.stderr.write("\rprocessed %d of %d documents" %
                         (done, len(docIds)))
saveBook(books[0], "B.xls")
saveBook(books[1], "A.xls")
