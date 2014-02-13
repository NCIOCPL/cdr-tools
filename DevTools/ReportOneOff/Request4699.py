#----------------------------------------------------------------------
#
# $Id$
#
# Excel report on GP specialties for COG.
#
# "We have had a request from the Assistant Director, Cancer Genetics
# Education Program at City of Hope for a report listing all of the
# professionals in the directory with their professional suffixes and
# specialties.  They want to be able to figure out percentages of people
# from different specialty areas, so if it could be done in a spreadsheet
# then they should be able to sort to get what they want.  I told her that
# we were in the process of converting the data so it could take a week or
# more to get the report."
#
# Modified 2009-11-18 at Margaret's request: the report had used the
# tables for "expertise provided" for showing specialties, but that's
# not what she wanted.  She has asked us to use the table which shows
# which boards the GPs have been certified by, or for which they are
# eligible for certification, or even those for which they would like
# to be certified, but aren't even eligible.
#
# BZIssue::4699
#
#----------------------------------------------------------------------
import cdrdb, ExcelWriter

GENPROF_HOST = 'mahler.nci.nih.gov'

#----------------------------------------------------------------------
# Collect the information needed for an individual GP.
#----------------------------------------------------------------------
class GP:
    def __init__(self, gpId, lastName, firstName):
        self.gpId = gpId
        self.name = (u"%s, %s" % (lastName, firstName)).strip()
        self.specialties = []
        cursor.execute("""\
            SELECT Degree
              FROM testdu.tblDegree
             WHERE MainID = ?
          ORDER BY DegreeSeq""", gpId)
        self.degrees = u"; ".join([r[0] for r in cursor.fetchall() if r[0]])
        cursor.execute("""\
            SELECT b."Desc"
              FROM testdu.lBoard b
              JOIN testdu.tblBoard m
                ON m.Code = b.Code
             WHERE m.MainID = ?
          ORDER BY 1""", gpId)
        for row in cursor.fetchall():
            self.specialties.append(row[0].strip())

#----------------------------------------------------------------------
# Create the Excel workbook, and set column headers and widths.
#----------------------------------------------------------------------
book = ExcelWriter.Workbook()
sheet = book.addWorksheet("GP Specialties")
hdrFont = ExcelWriter.Font("blue", bold = True)
centered = ExcelWriter.Alignment("Center")
hdrStyle = book.addStyle(alignment = centered, font = hdrFont)
row = sheet.addRow(1, hdrStyle)
sheet.addCol(1, 100)
sheet.addCol(2, 100)
sheet.addCol(3, 150)
row.addCell(1, "Name")
row.addCell(2, "Professional Suffixes")
row.addCell(3, "Specialty")

#----------------------------------------------------------------------
# Collect the rows from the main table for the active GPs.
#----------------------------------------------------------------------
cursor = cdrdb.connect(db='genprof', dataSource = GENPROF_HOST).cursor()
cursor.execute("""\
    SELECT ID, Last_Name, First_Name
      FROM testdu.tblMain
     WHERE PostToWeb = 1
  ORDER BY 2, 3""")
rows = cursor.fetchall()

#----------------------------------------------------------------------
# For each GP add a row for each of his/her specialties.  For a GP with
# no specialties, create a single row with a blank third column anyway.
#----------------------------------------------------------------------
rowNumber = 2
for gpId, lastName, firstName in rows:
    gp = GP(gpId, lastName, firstName)
    if not gp.specialties:
        row = sheet.addRow(rowNumber)
        rowNumber += 1
        row.addCell(1, gp.name)
        row.addCell(2, gp.degrees)
        row.addCell(3, '')
    else:
        for specialty in gp.specialties:
            row = sheet.addRow(rowNumber)
            rowNumber += 1
            row.addCell(1, gp.name)
            row.addCell(2, gp.degrees)
            row.addCell(3, specialty)

#----------------------------------------------------------------------
# Drop the workbook in the web server's root directory on the production
# system.
#----------------------------------------------------------------------
fp = open("b:/Inetpub/wwwroot/Request4699-boards.xls", "wb")
book.write(fp, True)
fp.close()
