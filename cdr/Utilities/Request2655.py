#----------------------------------------------------------------------
#
# $Id: Request2655.py,v 1.1 2006-11-28 15:00:37 bkline Exp $
#
# For the pilot phase of this project, provide Oncore with an Excel file that
# maps CTEP Institutions codes to CDR Organization IDs and Names. The External
# Map table with the Usage_map of CTEP_Institution_Code and the mapped CDR ID
# can be the source of this report.
#
# Also, provide Oncore with an Excel file that finds Active Person documents
# linked to the following Organizations and also the corresponding
# CTSU_Person_ID if any in the External Map table.
#
# Vanderbilt-Ingram Cancer Center - 31118
# Vanderbilt Ingram Cancer Center at Franklin 305822
#
# Barbara Ann Karmanos Cancer Institute - 31995
#
# We may add additional institutions to this report
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdrdb, ExcelWriter, sys, time

cursor = cdrdb.connect('CdrGuest').cursor()
cursor.execute("""\
    SELECT m.value, m.doc_id, n.value
      FROM external_map m
      JOIN external_map_usage u
        ON u.id = m.usage
      JOIN query_term n
        ON n.doc_id = m.doc_id
     WHERE n.path = '/Organization/OrganizationNameInformation'
                  + '/OfficialName/Name'
       AND u.name = 'CTEP_Institution_Code'
  ORDER BY m.value""")
book = ExcelWriter.Workbook()
sheet = book.addWorksheet('CTEP Institution Codes', frozenRows = 1)
sheet.addCol(1, 100)
sheet.addCol(2, 100)
sheet.addCol(3, 450)
bold = ExcelWriter.Font(bold = True)
centered = ExcelWriter.Alignment("Center")
headingStyle = book.addStyle(font = bold, alignment = centered)
row = sheet.addRow(1)
row.addCell(1, "CTEP CODE", "String", headingStyle)
row.addCell(2, "PDQ ID", "String", headingStyle)
row.addCell(3, "Organization Name", headingStyle)
rowNumber = 2
for ctepCode, pdqId, orgName in cursor.fetchall():
    row = sheet.addRow(rowNumber)
    row.addCell(1, ctepCode)
    row.addCell(2, u"CDR%d" % pdqId)
    row.addCell(3, orgName)
    rowNumber += 1
cursor.execute("""\
SELECT DISTINCT m.value, d.id, d.title
           FROM document d
           JOIN query_term o
             ON d.id = o.doc_id
LEFT OUTER JOIN external_map m
             ON m.doc_id = d.id
            AND m.usage = (SELECT id
                             FROM external_map_usage
                            WHERE name = 'CTSU_Person_ID')
          WHERE o.path LIKE '/Person%/@cdr:ref'
            AND d.active_status = 'A'
            AND o.int_val IN (31118, 305822, 31995)
       ORDER BY m.value, d.id""")
sheet = book.addWorksheet('Venderbilt and Karmanos Persons', frozenRows = 1)
sheet.addCol(1, 100)
sheet.addCol(2, 100)
sheet.addCol(3, 450)
row = sheet.addRow(1)
row.addCell(1, "CTEP CODE", "String", headingStyle)
row.addCell(2, "PDQ ID", "String", headingStyle)
row.addCell(3, "Organization Name", headingStyle)
rowNumber = 2
for ctepCode, pdqId, personName in cursor.fetchall():
    row = sheet.addRow(rowNumber)
    row.addCell(1, ctepCode or u"[unmapped]")
    row.addCell(2, u"CDR%d" % pdqId)
    row.addCell(3, personName)
    rowNumber += 1
if sys.platform == "win32":
    import os, msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
t = time.strftime("%Y%m%d%H%M%S")
print "Content-type: application/vnd.ms-excel"
print "Content-Disposition: attachment; filename=Percipenz-%s.xls" % t
print ""
book.write(sys.stdout, True)
