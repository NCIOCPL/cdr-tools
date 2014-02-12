#----------------------------------------------------------------------
#
# $Id$
#
# Report on CTEP and DCP active trials for CTRP.
#
#----------------------------------------------------------------------
import cdr, cdrdb, time, sys, lxml.etree as etree, ExcelWriter

class Trial:
    def __init__(self, docId, tree, status = ''):
        self.docId = docId
        self.ctepId = self.dcpId = self.nctId = ''
        self.status = status
        for node in tree.findall('ProtocolIDs/OtherID'):
            idString = idType = ''
            for child in node:
                if child.tag == 'IDType':
                    idType = child.text.strip().upper()
                elif child.tag == 'IDString':
                    idString = child.text.strip()
            if idType == 'CTEP ID':
                self.ctepId = idString
            elif idType == 'DCP ID':
                self.dcpId = idString
            elif idType == 'CLINICALTRIALS.GOV ID':
                self.nctId = idString
        if not self.status:
            for node in tree.findall('ProtocolAdminInfo/CurrentProtocolStatus'):
                self.status = node.text

def getCtgovStatus(cursor, docId):
    cursor.execute("""\
        SELECT value
          FROM query_term
         WHERE path = '/CTGovProtocol/OverallStatus'
           AND doc_id = ?""", docId)
    rows = cursor.fetchall()
    return rows and rows[0][0] or ''

def getSources(tree):
    sources = set()
    for node in tree.findall('ProtocolSources/ProtocolSource/SourceName'):
        sources.add(node.text.strip().upper())
    return sources

def makeSheet(book, hdrStyle, name, source):
    sheet = book.addWorksheet(name)
    sheet.addCol(1, 50)
    sheet.addCol(2, source == 'CTEP' and 300 or 200)
    sheet.addCol(3, 100)
    sheet.addCol(4, 150)
    row = sheet.addRow(1, hdrStyle)
    row.addCell(1, 'CDR ID')
    row.addCell(2, '%s ID' % source)
    row.addCell(3, 'NCT ID')
    row.addCell(4, 'Current Status')
    return sheet

def reportInScope(cursor, book, hdrStyle):
    ctepSheet = makeSheet(book, hdrStyle, 'CTEP Trials', 'CTEP')
    dcpSheet  = makeSheet(book, hdrStyle, 'DCP Trials', 'DCP')
    ctepRow = dcpRow = 2
    cursor.execute("""\
        SELECT DISTINCT q.doc_id
                   FROM query_term q
                   JOIN pub_proc_cg p
                     ON p.id = q.doc_id
                  WHERE q.path = '/InScopeProtocol/ProtocolSources'
                               + '/ProtocolSource/SourceName'
                    AND q.value IN ('NCI-CTEP', 'NCI-DCP')""", timeout=300)
    docIds = [row[0] for row in cursor.fetchall()]
    done = 0
    active = []
    for docId in docIds:
        cursor.execute("SELECT xml FROM document WHERE id = ?", docId)
        docXml = cursor.fetchall()[0][0]
        tree = etree.XML(docXml.encode('utf-8'))
        statuses = cdr.ProtocolStatusHistory(tree)
        if statuses.wasActive('2009-01-01'):
            trial = Trial(docId, tree)
            if trial.ctepId or trial.dcpId:
                active.append(trial)
        done += 1
        sys.stderr.write("\rprocessed %d of %d trials; %d matches" %
                         (done, len(docIds), len(active)))
    for trial in active:
        if trial.dcpId:
            row = dcpSheet.addRow(dcpRow)
            dcpRow += 1
            col2 = trial.dcpId
        else:
            row = ctepSheet.addRow(ctepRow)
            ctepRow += 1
            col2 = trial.ctepId
        row.addCell(1, trial.docId)
        row.addCell(2, col2)
        row.addCell(3, trial.nctId)
        row.addCell(4, trial.status)
    sys.stderr.write("\n")

def reportCtGov(cursor, book, hdrStyle):
    ctepSheet = makeSheet(book, hdrStyle, 'Transferred CTEP Trials', 'CTEP')
    dcpSheet  = makeSheet(book, hdrStyle, 'Transferred DCP Trials', 'DCP')
    ctepRow = dcpRow = 2
    cursor.execute("""\
        SELECT d.id
          FROM active_doc d
          JOIN pub_proc_cg p
            ON p.id = d.id
          JOIN doc_type t
            ON t.id = d.doc_type
         WHERE t.name = 'CTGovProtocol'""", timeout=300)
    docIds = [row[0] for row in cursor.fetchall()]
    checked = transferred = ctepOrDcp = 0
    active = []
    wantedSources = set(['NCI-CTEP', 'NCI-DCP'])
    for docId in docIds:
        cursor.execute("""\
            SELECT MAX(v.num)
              FROM doc_version v
              JOIN doc_type t
                ON t.id = v.doc_type
             WHERE t.name = 'InScopeProtocol'
               AND v.id = ?""", docId, timeout=300)
        rows = cursor.fetchall()
        if rows and rows[0][0]:
            cursor.execute("""\
                SELECT xml
                  FROM doc_version
                 WHERE id = ?
                   AND num = ?""", (docId, rows[0][0]), timeout=300)
            docXml = cursor.fetchall()[0][0]
            tree = etree.XML(docXml.encode('utf-8'))
            sources = getSources(tree)
            if wantedSources.intersection(sources):
                statuses = cdr.ProtocolStatusHistory(tree)
                if statuses.wasActive('2009-01-01'):
                    status = getCtgovStatus(cursor, docId)
                    trial = Trial(docId, tree, status)
                    if trial.dcpId or trial.ctepId:
                        active.append(trial)
                ctepOrDcp += 1
            transferred += 1
        checked += 1
        sys.stderr.write("\rprocessed %d of %d trials; %d transferred; "
                         "%d CTEP or DCP; %d active" %
                         (checked, len(docIds), transferred, ctepOrDcp,
                          len(active)))
    for trial in active:
        if trial.dcpId:
            row = dcpSheet.addRow(dcpRow)
            dcpRow += 1
            col2 = trial.dcpId
        else:
            row = ctepSheet.addRow(ctepRow)
            ctepRow += 1
            col2 = trial.ctepId
        row.addCell(1, trial.docId)
        row.addCell(2, col2)
        row.addCell(3, trial.nctId)
        row.addCell(4, trial.status)

def main():
    cursor = cdrdb.connect('CdrGuest').cursor()
    book = ExcelWriter.Workbook()
    alignment = ExcelWriter.Alignment('Center', 'Center')
    font = ExcelWriter.Font(bold=True)
    hdrStyle = book.addStyle(font=font, alignment=alignment)
    reportInScope(cursor, book, hdrStyle)
    reportCtGov(cursor, book, hdrStyle)
    fp = open('d:/Inetpub/wwwroot/report4896.xls', 'wb')
    book.write(fp, True)
    fp.close()

if __name__ == '__main__':
    main()
