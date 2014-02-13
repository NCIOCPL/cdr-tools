#----------------------------------------------------------------------
#
# $Id$
#
# Excel spreadsheet for CTEP for Completion Date
#
# "We need to create a spreadsheet of trials that meet the same criteria used
# for the Completion Date email and web-based update, with the additional
# criteria of including only the trials for which we have SourceName =
# NCI-CTEP. The spreadsheet needs the following:
#
#   CDRID CTEPID    Official Title     Start Date 
#
#   CTEP ID for the protocol is the OtherID element that has IDType of CTEP ID.
#
# I need to send this to CTEP by Tuesday - sorry for the tight deadline again!"
#
# BZIssue::3777
#
#----------------------------------------------------------------------

import cdr, cdrdb, re, sys, xml.dom.minidom, xml.sax.saxutils, ExcelWriter

class ProtocolDate:
    def __init__(self, date, dateType):
        self.dateType = dateType
        self.date     = date
    def ok(self):
        return self.dateType and self.date and True or False
    def __str__(self):
        return u"%s (%s)" % (self.date or u"DATE EMPTY",
                             self.dateType or u"NO DATE TYPE")

class Trial:
    def __cmp__(self, other):
        return cmp(self.docId, other.docId)
    def __init__(self, docId, cursor):
        self.docId      = docId
        self.title      = None
        self.protId     = None
        self.ctepId     = None
        self.startDates = []
        self.startDate  = None
        cursor.execute("""\
         SELECT d.value, t.value
           FROM query_term d
LEFT OUTER JOIN query_term t
             ON d.doc_id = t.doc_id
            AND LEFT(d.node_loc, 8) = LEFT(t.node_loc, 8)
          WHERE d.doc_id = ?
            AND d.path = '/InScopeProtocol/ProtocolAdminInfo/StartDate'
            AND t.path = '/InScopeProtocol/ProtocolAdminInfo/StartDate'
                       + '/@DateType'""", docId, timeout = 300)
        for startDate, dateType in cursor.fetchall():
            self.startDates.append(ProtocolDate(startDate, dateType))
        self.startDate = self.getBestStartDate()
        cursor.execute("""\
    SELECT p.value, t.value
      FROM query_term p
      JOIN query_term t
        ON p.doc_id = t.doc_id
       AND LEFT(p.node_loc, 4) = LEFT(t.node_loc, 4)
     WHERE p.path = '/InScopeProtocol/ProtocolTitle'
       AND t.path = '/InScopeProtocol/ProtocolTitle/@Type'
       AND t.value IN ('Professional', 'Original')
       AND p.doc_id = ?""", docId, timeout = 300)
        originalTitle = None
        professionalTitle = None
        for title, titleType in cursor.fetchall():
            title = title.strip()
            titleType = titleType.upper()
            if title:
                if titleType == 'ORIGINAL':
                    originalTitle = title
                elif titleType == 'PROFESSIONAL':
                    professionalTitle = title
        if originalTitle:
            self.title = originalTitle
        elif professionalTitle:
            self.title = professionalTitle
        cursor.execute("""\
        SELECT value
          FROM query_term
         WHERE path = '/InScopeProtocol/ProtocolIDs/PrimaryID/IDString'
           AND doc_id = ?""", docId, timeout = 300)
        rows = cursor.fetchall()
        if rows:
            protId = rows[0][0].strip()
            if protId:
                self.protId = protId
        cursor.execute("""\
        SELECT i.value
          FROM query_term i
          JOIN query_term t
            ON t.doc_id = i.doc_id
           AND LEFT(t.node_loc, 8) = LEFT(i.node_loc, 8)
         WHERE i.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDString'
           AND t.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
           AND t.value = 'CTEP ID'
           AND i.doc_id = ?""", docId, timeout = 300)
        rows = cursor.fetchall()
        if rows:
            ctepId = rows[0][0].strip()
            if ctepId:
                self.ctepId = ctepId
    def getBestStartDate(self):
        if len(self.startDates) == 1:
            return self.startDates[0]
        startDate = None
        for d in self.startDates:
            if d.dateType == 'Actual':
                if startDate:
                    raise Exception("CDR%d has multiple 'Actual' start dates" %
                                    self.docId)
                startDate = d
        if self.startDates:
            raise Exception("CDR%d has multiple start dates, none of which "
                            "has date type 'Actual'" % self.docId)
        return startDate
    def getStartDateHtml(self):
        if self.startDate:
            return u"%s start date: %s" % (self.startDate.dateType or "",
                                           self.startDate.date)
        return u"no start dates found"

conn = cdrdb.connect()
cursor = conn.cursor()
docIdFilename = len(sys.argv) > 1 and sys.argv[1] or 'issue3757-bach-ids.txt'
fp = open(docIdFilename)
docIds = []
for line in fp:
    docIds.append(int(line.strip()))
fp.close()
n = 0
cursor.execute("""\
    SELECT DISTINCT doc_id
      FROM query_term
     WHERE path = '/InScopeProtocol/ProtocolSources/ProtocolSource/SourceName'
       AND value = 'NCI-CTEP'""")
ctepTrials = set([row[0] for row in cursor.fetchall()])
trials = []
for docId in docIds:
    if docId in ctepTrials:
        trials.append(Trial(docId, cursor))
    n += 1
    sys.stderr.write("\rprocessed %d of %d trials" % (n, len(docIds)))

wb = ExcelWriter.Workbook()
sheet = wb.addWorksheet('CTEP Protocols')
row = sheet.addRow(1)
row.addCell(1, "CDR ID")
row.addCell(2, "CTEP ID")
row.addCell(3, "Title")
row.addCell(4, "Start Date")
rowNum = 2
trials.sort()
for trial in trials:
    row = sheet.addRow(rowNum)
    rowNum += 1
    row.addCell(1, trial.docId)
    row.addCell(2, trial.ctepId)
    row.addCell(3, trial.title.replace("\r", "").replace("\n", " "))
    if trial.startDate and trial.startDate.date:
        row.addCell(4, trial.startDate.date)
fp = file('Issue3777.xls', 'wb')
wb.write(fp, True)
fp.close()
