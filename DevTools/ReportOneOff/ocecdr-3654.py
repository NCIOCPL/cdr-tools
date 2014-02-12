#----------------------------------------------------------------------
#
# $Id$
#
# We would like to review the Purpose Text in patient summaries to
# examine the appropriateness of the language/reading level since
# they were mapped from the HP summaries. We think it would be ideal
# to review this in a spreadsheet.
#
#----------------------------------------------------------------------
import cdrdb, lxml.etree as etree, xlwt

def lookupBoard(docId, cursor):
    cursor.execute("""\
SELECT int_val
  FROM query_term
 WHERE path = '/Summary/TranslationOf/@cdr:ref'
   AND doc_id = ?""", docId)
    rows = cursor.fetchall()
    if rows:
        return lookupBoard(rows[0][0], cursor)
    cursor.execute("""\
SELECT value
  FROM query_term
 WHERE path = '/Summary/SummaryMetaData/PDQBoard/Board'
   AND doc_id = ?""", docId)
    rows = cursor.fetchall()
    if not rows:
        return None
    return mapBoard(rows[0][0])

def mapBoard(string):
    if string is None:
        return None
    if "complementary and alternative" in string.lower():
        return "CAM"
    if "adult treatment" in string.lower():
        return "Adult"
    if "pediatric" in string.lower():
        return "Pediatric"
    if "screening" in string.lower():
        return "Screening"
    if "supportive" in string.lower():
        return "Supportive"
        
class Summary:
    def __init__(self, docId, cursor):
        self.docId = docId
        self.title = self.purpose = None
        self.board = lookupBoard(docId, cursor)
        cursor.execute("SELECT xml FROM document WHERE id = ?", docId)
        xml = cursor.fetchall()[0][0]
        tree = etree.XML(xml.encode("utf-8"))
        for node in tree.findall("SummaryTitle"):
            self.title = u"".join(node.itertext())
        for node in tree.findall("SummaryMetaData/PurposeText"):
            self.purpose = u"".join(node.itertext())
        return
        for node in tree.findall("SummaryMetaData/PDQBoard/Board"):
            board = lookupBoard(node.text, cursor)
            if board:
                self.board = board
                break
    def __cmp__(self, other):
        return cmp(self.docId, other.docId)

cursor = cdrdb.connect("CdrGuest").cursor()
cursor.execute("""\
SELECT DISTINCT q.doc_id
           FROM query_term q
           JOIN active_doc a
             ON a.id = q.doc_id
           JOIN pub_proc_cg c
             ON c.id = a.id
          WHERE q.path = '/Summary/SummaryMetaData/SummaryAudience'
            AND q.value = 'Patients'""")
boards = {}
for row in cursor.fetchall():
    summary = Summary(row[0], cursor)
    if True or summary.board:
        if summary.board not in boards:
            boards[summary.board] = []
        boards[summary.board].append(summary)
book = xlwt.Workbook()
boardNames = boards.keys()
boardNames.sort()
headerStyle = xlwt.XFStyle()
alignment = xlwt.Alignment()
alignment.horz = xlwt.Alignment.HORZ_CENTER
font = xlwt.Font()
font.bold = True
headerStyle.font = font
headerStyle.alignment = alignment
dataStyle = xlwt.XFStyle()
alignment = xlwt.Alignment()
alignment.vert = xlwt.Alignment.VERT_TOP
alignment.wrap = xlwt.Alignment.WRAP_AT_RIGHT
dataStyle.alignment = alignment
for boardName in boardNames:
    sheet = book.add_sheet(unicode(boardName))
    sheet.write(0, 0, "CDR ID", headerStyle)
    sheet.write(0, 1, "Title", headerStyle)
    sheet.write(0, 2, "Purpose Text", headerStyle)
    sheet.col(1).width = sheet.col(2).width = 15000
    rowNum = 1
    summaries = boards[boardName]
    summaries.sort()
    for summary in summaries:
        sheet.write(rowNum, 0, summary.docId, dataStyle)
        sheet.write(rowNum, 1, summary.title, dataStyle)
        sheet.write(rowNum, 2, summary.purpose, dataStyle)
        rowNum += 1
book.save("ocecdr-3654.xls")
