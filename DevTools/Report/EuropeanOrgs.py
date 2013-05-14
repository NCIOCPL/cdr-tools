#----------------------------------------------------------------------
#
# $Id: $
#
# Report identifying lead organizations in europe
#
#----------------------------------------------------------------------
import cdr, cdrdb, sys, time, cdrcgi, ExcelWriter

if sys.platform == "win32":
    import os, msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

conn = cdrdb.connect('CdrGuest')
conn.setAutoCommit()
cursor = conn.cursor()

# Excel is able to read XML files so that's what we create here
# -------------------------------------------------------------
stamp = time.strftime("%Y%m%dT%H%M%S")
REPORTS_BASE = 'd:/cdr/tmp'
name = '/EuropeanOrgs_%s.xml' % stamp
fullname = REPORTS_BASE + name

#----------------------------------------------------------------------
# Find InScopeProtocol documents with organization in France
# Note:  In order to make sure the documents we're retrieving are 
#        also on Cancer.gov, we are linking against pub_proc_cg, which
#        keeps a copy of each document submitted to Cancer.gov and not
#        yet deleted.
#----------------------------------------------------------------------
cursor.execute("""\
      SELECT o.value AS "Org", org.value AS "OrgName", p.value AS "Role", 
             d.id AS "CDR-ID", pn.value as "Protocol",  x.value AS "NCT-ID", 
             ps.value AS "Status", s.value AS "Country"
        FROM document d
        JOIN doc_type dt
          ON dt.id = d.doc_type
        JOIN query_term p
          ON p.doc_id = d.id
         AND p.path = '/InScopeProtocol/ProtocolAdminInfo' +
                      '/ProtocolLeadOrg/LeadOrgRole'
        JOIN query_term ps
          ON d.id = ps.doc_id
         AND ps.path = '/InScopeProtocol/ProtocolAdminInfo' +
                       '/CurrentProtocolStatus'
        JOIN query_term pn
          ON pn.doc_id = p.doc_id
         AND pn.path = '/InScopeProtocol/ProtocolIDs' +
                       '/PrimaryID/IDString'
        JOIN query_term o
          ON o.doc_id = p.doc_id
         AND o.path = '/InScopeProtocol/ProtocolAdminInfo' +
                       '/ProtocolLeadOrg/LeadOrganizationID/@cdr:ref'
         AND left(o.node_loc, 8) = left(p.node_loc, 8)
        JOIN query_term org
          ON org.doc_id = o.int_val
         AND org.path = '/Organization/OrganizationNameInformation' +
                       '/OfficialName/Name'
        JOIN query_term c
          ON c.doc_id = o.int_val
         AND c.path = '/Organization/OrganizationLocations/CIPSContact'
        JOIN query_term a
          ON o.int_val = a.doc_id
         AND c.value = a.value
         AND a.path = '/Organization/OrganizationLocations' +
                       '/OrganizationLocation/Location/@cdr:id'
        JOIN query_term s
          ON a.doc_id = s.doc_id
         AND s.path = '/Organization/OrganizationLocations' +
                       '/OrganizationLocation/Location/PostalAddress/Country'
         AND left(a.node_loc, 12) = left(s.node_loc, 12)
        JOIN query_term g
          ON g.doc_id = d.id
         AND g.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
         AND g.value = 'ClinicalTrials.gov ID'
        JOIN query_term x
          ON x.doc_id = g.doc_id
         AND x.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDString'
         AND LEFT(x.node_loc, 8) = LEFT(g.node_loc, 8)
       WHERE name = 'InScopeProtocol'
         AND p.value = 'Primary'
         AND s.value not in ('U.S.A.', 'Canada')
         AND s.value not in ('Argentina',   'Australia', 'Brazil',
                             'Chile',       'China',     'Colombia',
                             'Costa Rica',  'Cuba',      'Honduras',
                             'India',       'Israel',    'Jamaica',
                             'Japan',       'Lebanon',   'Mexico',
                             'New Zealand', 'Peru',      'Puerto Rico',
                             'Republic of Korea', 'Republic of Singapore',
                             'Republic of South Africa',
                             'Taiwan, Province of China',
                             'Uruguay',     'Venezuela')
       ORDER BY org.value, ps.value
""", timeout = 600)
rows = cursor.fetchall()

# Create the spreadsheet and define default style, etc.
# -----------------------------------------------------
wb      = ExcelWriter.Workbook()
b       = ExcelWriter.Border()
borders = ExcelWriter.Borders(b, b, b, b)
font    = ExcelWriter.Font(name = 'Times New Roman', size = 11)
align   = ExcelWriter.Alignment('Left', 'Top', wrap = True)
style1  = wb.addStyle(alignment = align, font = font)
urlFont = ExcelWriter.Font('blue', None, 'Times New Roman', size = 11)
style4  = wb.addStyle(alignment = align, font = urlFont)
ws      = wb.addWorksheet("Org-trials in Europe", style1, 45, 1)
style2  = wb.addStyle(alignment = align, font = font, 
                         numFormat = 'YYYY-mm-dd')
    
# Set the colum width
# -------------------
ws.addCol( 1, 60)
ws.addCol( 2, 400)
ws.addCol( 3, 60)
ws.addCol( 4, 60)
ws.addCol( 5, 150)
ws.addCol( 6, 80)
ws.addCol( 7, 80)
ws.addCol( 8, 100)

# Create the Header row
# ---------------------
exRow = ws.addRow(1, style2)
exRow.addCell(1, 'Org ID')
exRow.addCell(2, 'Org Name')
exRow.addCell(3, 'Role')
exRow.addCell(4, 'Prot ID')
exRow.addCell(5, 'Protocol Name')
exRow.addCell(6, 'NCT-ID')
exRow.addCell(7, 'Protocol Status')
exRow.addCell(8, 'Country')

# Add the protocol data one record at a time beginning after 
# the header row
# ----------------------------------------------------------
rowNum = 1
for row in rows:
    rowNum += 1
    exRow = ws.addRow(rowNum, style1, 40)
    exRow.addCell(1, cdr.exNormalize(row[0])[1], style = style2)
    exRow.addCell(2, row[1], style = style2)
    exRow.addCell(3, row[2], style = style2)
    exRow.addCell(4, cdr.exNormalize(row[3])[1], style = style2)
    exRow.addCell(5, row[4], style = style2)
    exRow.addCell(6, row[5], style = style2)
    exRow.addCell(7, row[6], style = style2)
    exRow.addCell(8, row[7], style = style2)

# Save the Report
# ---------------
fobj = file(fullname, "w")
wb.write(fobj)
print ""
print "  Report written to %s" % fullname
fobj.close()

