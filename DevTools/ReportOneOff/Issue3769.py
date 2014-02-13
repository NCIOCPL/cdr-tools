#----------------------------------------------------------------------
#
# $Id$
#
# Report Listing Outcome Measures
#
# "We need a spreadsheet report that lists CDRID, HP Protocol Title, Primary
# and Secondary Outcome measures. Both Primary and Secondary Outcomes are
# multiply occurring. We need this for the same set of trials that we selected
# for the Completeion Date mailer, without the CTEP exception."
#
# BZIssue::3769
#
#----------------------------------------------------------------------

import cdr, cdrdb, re, sys, xml.dom.minidom, ExcelWriter

class Outcome:
    def __init__(self, node):
        self.outcomeType = node.getAttribute('OutcomeType')
        self.outcomeText = cdr.getTextContent(node).strip()

class Trial:
    def __cmp__(self, other):
        return cmp(self.docId, other.docId)
    def __init__(self, docId, cursor):
        self.docId      = docId
        self.title      = None
        self.primary    = []
        self.secondary  = []
        cursor.execute("SELECT xml FROM document WHERE id = ?", docId)
        docXml = cursor.fetchall()[0][0]
        dom = xml.dom.minidom.parseString(docXml.encode('utf-8'))
        for node in dom.documentElement.childNodes:
            if node.nodeName == 'ProtocolTitle':
                if node.getAttribute('Type') == 'Professional':
                    title = cdr.getTextContent(node).strip()
                    if title:
                        self.title = title
        for node in dom.getElementsByTagName('Outcome'):
            outcome = Outcome(node)
            if outcome.outcomeText:
                if outcome.outcomeType == 'Primary':
                    self.primary.append(outcome.outcomeText)
                else:
                    self.secondary.append(outcome.outcomeText)

conn = cdrdb.connect()
cursor = conn.cursor()
docIdFilename = len(sys.argv) > 1 and sys.argv[1] or 'issue3757-bach-ids.txt'
fp = open(docIdFilename)
docIds = []
for line in fp:
    docIds.append(int(line.strip()))
fp.close()
n = 0
trials = []
for docId in docIds:
    trials.append(Trial(docId, cursor))
    n += 1
    sys.stderr.write("\rprocessed %d of %d trials" % (n, len(docIds)))

wb = ExcelWriter.Workbook()
sheet = wb.addWorksheet('Outcomes')
row = sheet.addRow(1)
row.addCell(1, "CDR ID")
row.addCell(2, "Title")
row.addCell(3, "Primary")
row.addCell(4, "Secondary")
rowNum = 2
trials.sort()

def fix(me):
    return me.replace("\r", "").replace("\n", " ")
for trial in trials:
    extraRows = 0
    numOutcomeRows = max(len(trial.primary), len(trial.secondary))
    if numOutcomeRows > 1:
        extraRows = numOutcomeRows - 1
    row = sheet.addRow(rowNum)
    rowNum += 1
    row.addCell(1, trial.docId, mergeDown = extraRows)
    row.addCell(2, trial.title, mergeDown = extraRows)
    if trial.primary:
        row.addCell(3, fix(trial.primary[0]))
    if trial.secondary:
        row.addCell(4, fix(trial.secondary[0]))
    i = 1
    while len(trial.primary) > i or len(trial.secondary) > i:
        row = sheet.addRow(rowNum)
        rowNum += 1
        if len(trial.primary) > i:
            row.addCell(3, fix(trial.primary[i]))
        if len(trial.secondary) > i:
            row.addCell(4, fix(trial.secondary[i]))
        i += 1

fp = file('Issue3769.xls', 'wb')
wb.write(fp, True)
fp.close()
