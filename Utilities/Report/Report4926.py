#----------------------------------------------------------------------
#
# $Id$
#
# Spreadsheet of sample glossary terms for pronunciation test.
#
# BZIssue::4926
#
#----------------------------------------------------------------------
import ExcelWriter, random, lxml.etree as etree, cdrdb, sys

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
random.shuffle(docIds)
book = ExcelWriter.Workbook()
sheet = book.addWorksheet('Term Names')
row = sheet.addRow(1)
row.addCell(1, "CDR ID")
row.addCell(2, "Term Name")
row.addCell(3, "Language")
row.addCell(4, "Pronunciation")
row.addCell(5, "Filename")
row.addCell(6, "Creator")
rowNumber = 2
done = used = 0
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

for docId in docIds:
    try:
        nameDoc = TermNameDoc(docId, cursor)
        if len(nameDoc.names) > 1 and nameDoc.names[0].pronunciation:
            for name in nameDoc.names:
                row = sheet.addRow(rowNumber)
                rowNumber += 1
                row.addCell(1, docId)
                row.addCell(2, name.string)
                row.addCell(3, name.language)
                if name.pronunciation:
                    row.addCell(4, name.pronunciation)
            used += 1
            if used >= 50:
                break
    except Exception, e:
        sys.stderr.write("\nCDR%d: %s\n" % (docId, e))
    finally:
        done += 1
        sys.stderr.write("\rprocessed %d of %d documents; used %d" %
                         (done, len(docIds), used))
fp = open('Report4926.xls', 'wb')
book.write(fp, True)
fp.close()
