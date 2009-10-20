#----------------------------------------------------------------------
#
# $Id$
#
# Report identifying protocol sites located in France.
# The output format is *.xml (Excel is able to import this)
#
# $Log: not supported by cvs2svn $
# Revision 1.2  2006/01/18 22:53:47  venglisc
# Modified the file name extension of the output file.
#
# Revision 1.1  2006/01/18 22:36:13  venglisc
# Initial copy of report listing protocols with sites in France. (Bug 1947)
#
#----------------------------------------------------------------------
import cdrdb, sys, time, cdrcgi, ExcelWriter

if sys.platform == "win32":
    import os, msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

conn = cdrdb.connect('CdrGuest')
conn.setAutoCommit()
cursor = conn.cursor()

# Excel is able to read XML files so that's what we create here
# -------------------------------------------------------------
t = time.strftime("%Y%m%d%H%M%S")
REPORTS_BASE = 'd:/cdr/tmp'
name = '/ProtocolSitesInFrance.xml'
fullname = REPORTS_BASE + name

#----------------------------------------------------------------------
# Find InScopeProtocol documents with organization in France
# Note:  In order to make sure the documents we're retrieving are 
#        also on Cancer.gov, we are linking against pub_proc_cg, which
#        keeps a copy of each document submitted to Cancer.gov and not
#        yet deleted.
#----------------------------------------------------------------------
cursor.execute("""\
SELECT d.id CDRID, pid.value ProtocolID, t.value Title
  FROM pub_proc_cg pp
  JOIN document d
    ON d.id = pp.id
  JOIN query_term stat
    ON stat.doc_id = d.id
  JOIN doc_type dt
    ON dt.id = d.doc_type
   AND dt.name in ('InScopeProtocol')
  JOIN query_term t
    ON d.id = t.doc_id
  JOIN query_term type
    ON d.id = type.doc_id
  JOIN query_term pid
    ON d.id = pid.doc_id
 WHERE d.active_status = 'A'
   AND stat.path  = '/InScopeProtocol/ProtocolAdminInfo/CurrentProtocolStatus'
   AND stat.value in ('Active', 'Approved-not yet active')
   AND pid.path   = '/InScopeProtocol/ProtocolIDs/PrimaryID/IDString'
   AND t.path     = '/InScopeProtocol/ProtocolTitle'
   AND type.path  = '/InScopeProtocol/ProtocolTitle/@Type'
   AND t.node_loc = type.node_loc
   AND type.value = 'Professional'
   AND pp.xml like '%ProtocolSites%France</Country%'
 ORDER BY t.value""", timeout = 300)
rows = cursor.fetchall()

# Create the spreadsheet and define default style, etc.
# -----------------------------------------------------
wb      = ExcelWriter.Workbook()
b       = ExcelWriter.Border()
borders = ExcelWriter.Borders(b, b, b, b)
font    = ExcelWriter.Font(name = 'Times New Roman', size = 11)
align   = ExcelWriter.Alignment('Left', 'Top', wrap = True)
style1  = wb.addStyle(alignment = align, font = font)
# style1  = wb.addStyle(alignment = align, font = font, borders = borders)
urlFont = ExcelWriter.Font('blue', None, 'Times New Roman', size = 11)
style4  = wb.addStyle(alignment = align, font = urlFont)
ws      = wb.addWorksheet("Clinical Trial Sites in France", style1, 45, 1)
style2  = wb.addStyle(alignment = align, font = font, 
                         numFormat = 'YYYY-mm-dd')
    
# Set the colum width
# -------------------
ws.addCol( 1, 50)
ws.addCol( 2, 150)
ws.addCol( 3, 550)

# Create the Header row
# ---------------------
exRow = ws.addRow(1, style2)
exRow.addCell(1, 'CDR-ID')
exRow.addCell(2, 'Protocol ID')
exRow.addCell(3, 'Protocol Title')

# Add the protocol data one record at a time beginning after 
# the header row
# ----------------------------------------------------------
rowNum = 1
for row in rows:
    rowNum += 1
    exRow = ws.addRow(rowNum, style1, 40)
    url = ("http://www.cancer.gov/clinicaltrials/"
           "view_clinicaltrials.aspx?version=healthprofessional&"
           "cdrid=%d" % row[0])
    exRow.addCell(1, row[0], href = url, style = style4)
    exRow.addCell(2, row[1], style = style2)
    exRow.addCell(3, row[2], style = style2)

#----------------------------------------------------------------------
# Find CTGovProtocol documents with organization in France
#----------------------------------------------------------------------
cursor.execute("""\
SELECT d.id CDRID, pid.value ProtocolID, t.value Title
  FROM pub_proc_cg pp
  JOIN document d
    ON d.id = pp.id
  JOIN query_term stat
    ON d.id = stat.doc_id
  JOIN doc_type dt
    ON dt.id = d.doc_type
   AND dt.name = 'CTGovProtocol'
  JOIN query_term pid
    ON d.id = pid.doc_id
  JOIN query_term t
    ON d.id = t.doc_id
   AND t.path = '/CTGovProtocol/BriefTitle'
 WHERE d.active_status = 'A'
   AND stat.path  = '/CTGovProtocol/OverallStatus'
   AND stat.value in ('Active', 'Approved-not yet active')
   AND pid.path   = '/CTGovProtocol/IDInfo/NCTID'
   AND pp.xml like '%Protocol%France</Country%'
 ORDER by t.value""", timeout = 300)
rows = cursor.fetchall()

# Add the protocol data one record at a time beginning after 
# the header row
# ----------------------------------------------------------
for row in rows:
    rowNum += 1
    exRow = ws.addRow(rowNum, style1, 40)
    url = ("http://www.cancer.gov/clinicaltrials/"
           "view_clinicaltrials.aspx?version=healthprofessional&"
           "cdrid=%d" % row[0])
    exRow.addCell(1, row[0], href = url, style = style4)
    exRow.addCell(2, row[1], style = style2)
    exRow.addCell(3, row[2], style = style2)

# Save the Report
# ---------------
fobj = file(fullname, "w")
wb.write(fobj)
print ""
print "  Report written to %s" % fullname
fobj.close()

