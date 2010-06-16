#----------------------------------------------------------------------
#
# $Id$
#
# Adhoc report of summary titles and pretty urls
#
# "We need to get a report in a spreadsheet that has the CDR ID, SummaryTitle,
# and SummaryURL (pretty url) for each English, Adult Treatment, Health
# Professional cancer information summary."
#
# BZIssue::3116
#
#----------------------------------------------------------------------
import cdrdb, ExcelWriter, re

pattern = re.compile("/cancertopics/pdq/treatment/(.*)/HealthProfessional",
                     re.I)
def extractUrl(u):
    if not u:
        return ""
    match = pattern.search(u)
    return match and match.group(1) or u

cursor = cdrdb.connect('CdrGuest').cursor()
cursor.execute("""\
    SELECT DISTINCT b.doc_id, t.value, u.value
               FROM query_term n
               JOIN query_term b
                 ON b.int_val = n.doc_id
               JOIN query_term a
                 ON a.doc_id = b.doc_id
               JOIN query_term l
                 ON l.doc_id = b.doc_id
               JOIN query_term t
                 ON t.doc_id = b.doc_id
    LEFT OUTER JOIN query_term u
                 ON u.doc_id = b.doc_id
              WHERE b.path = '/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref'
                AND n.path = '/Organization/OrganizationNameInformation'
                           + '/OfficialName/Name'
                AND n.value = 'PDQ Adult Treatment Editorial Board'
                AND a.path = '/Summary/SummaryMetaData/SummaryAudience'
                AND a.value = 'Health professionals'
                AND l.path = '/Summary/SummaryMetaData/SummaryLanguage'
                AND l.value = 'English'
                AND u.path = '/Summary/SummaryMetaData/SummaryURL/@cdr:xref'
                AND t.path = '/Summary/SummaryTitle'
           ORDER BY t.value""", timeout = 300)

book = ExcelWriter.Workbook()
sheet = book.addWorksheet('English HP Treatment Summaries', frozenRows = 1)
row = sheet.addRow(1)
row.addCell(1, 'CDR ID')
row.addCell(2, 'Summary Title')
row.addCell(3, 'Pretty URL')
rowNum = 2
for cdrId, title, url in cursor.fetchall():
    row = sheet.addRow(rowNum)
    row.addCell(1, cdrId)
    row.addCell(2, title)
    row.addCell(3, extractUrl(url))
    rowNum += 1
fp = file('Request3116.xls', 'wb')
book.write(fp, True)
