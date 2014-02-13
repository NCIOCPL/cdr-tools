#----------------------------------------------------------------------
#
# $Id$
#
# One-time Excel report of Clinical Trial Office information on Org records.
#
# "We need to provide CTEP with a one time report in Excel format with
# Clinical Trial Office Information that we have for Org records.
#
# For CDR Org records that are in the External Map table with a mapping to
# CTEP Institution Code, check if they have in their CDRORG record a
# ClinicalTrialsOffice contact block. If they do, include in spreadsheet
# with following columns:
#
#    PDQ Org ID
#    PDQ Organization Name
#    CTEP Institution Code
#    Clinical Trial Office Contact Name
#    Clinical Trial Office Contact Phone
#    Clinical Trial Office Contact Email"
#
# BZIssue::4729
#
#----------------------------------------------------------------------
import cdrdb, ExcelWriter

#----------------------------------------------------------------------
# Create the Excel worksheet, and set column headers and widths.
#----------------------------------------------------------------------
def createSheet(book):
    sheet = book.addWorksheet("CTEP Orgs")
    hdrFont = ExcelWriter.Font("blue", bold = True)
    centered = ExcelWriter.Alignment("Center")
    hdrStyle = book.addStyle(alignment = centered, font = hdrFont)
    row = sheet.addRow(1, hdrStyle)
    sheet.addCol(1, 50)
    sheet.addCol(2, 100)
    sheet.addCol(3, 100)
    sheet.addCol(4, 200)
    sheet.addCol(5, 200)
    sheet.addCol(6, 200)
    row.addCell(1, "PDQ Org ID")
    row.addCell(2, "PQ Organization Name")
    row.addCell(3, "CTEP Institution Code")
    row.addCell(4, "Clinical Trial Office Contact Name")
    row.addCell(5, "Clinical Trial Office Contact Phone")
    row.addCell(6, "Clinical Trial Office Contact Email")
    return sheet

#----------------------------------------------------------------------
# Get the official name for an organization.
#----------------------------------------------------------------------
def getOrgName(cursor, cdrId):
    cursor.execute("""\
        SELECT value
          FROM query_term
         WHERE path = '/Organization/OrganizationNameInformation'
                    + '/OfficialName/Name'
           AND doc_id = ?""", cdrId)
    rows = cursor.fetchall()
    return rows and rows[0][0].strip() or u""

#----------------------------------------------------------------------
# Get one of the CTO contact information pieces.
#----------------------------------------------------------------------
def getContactValue(cursor, cdrId, name):
    cursor.execute("""\
        SELECT value
          FROM query_term
         WHERE path = '/Organization/OrganizationLocations'
                    + '/ClinicalTrialsOfficeContact'
                    + '/ClinicalTrialsOfficeContact%s'
           AND doc_id = ?""" % name, cdrId)
    rows = cursor.fetchall()
    return rows and rows[0][0].strip() or u""

#----------------------------------------------------------------------
# Populate a row in the sheet.
#----------------------------------------------------------------------
def addRow(sheet, cdrId, ctepId, rowNumber, cursor):
    row = sheet.addRow(rowNumber)
    row.addCell(1, cdrId)
    row.addCell(2, getOrgName(cursor, cdrId))
    row.addCell(3, ctepId)
    row.addCell(4, getContactValue(cursor, cdrId, 'Name'))
    row.addCell(5, getContactValue(cursor, cdrId, 'Phone'))
    row.addCell(6, getContactValue(cursor, cdrId, 'Email'))

#----------------------------------------------------------------------
# Collect the organization IDs.
#----------------------------------------------------------------------
def collectOrgIds(cursor):
    cursor.execute("""\
        SELECT DISTINCT m.doc_id, m.value
                   FROM external_map m
                   JOIN external_map_usage u
                     ON u.id = m.usage
                   JOIN query_term c
                     ON c.doc_id = m.doc_id
                  WHERE u.name = 'CTEP_Institution_Code'
                    AND c.path = '/Organization/OrganizationLocations'
                               + '/ClinicalTrialsOfficeContact/@cdr:id'
               ORDER BY m.doc_id, m.value""")
    return cursor.fetchall()

#----------------------------------------------------------------------
# Create the report
#----------------------------------------------------------------------
def main():
    book = ExcelWriter.Workbook()
    sheet = createSheet(book)
    rowNumber = 2
    cursor = cdrdb.connect().cursor()
    for cdrId, ctepId in collectOrgIds(cursor):
        addRow(sheet, cdrId, ctepId, rowNumber, cursor)
        rowNumber += 1
    fp = open('d:/Inetpub/wwwroot/Request4729.xls', 'wb')
    book.write(fp, True)
    fp.close()

if __name__ == '__main__':
    main()
