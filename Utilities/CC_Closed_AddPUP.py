#----------------------------------------------------------------------
#
# $Id: CC_Closed_AddPUP.py,v 1.1 2009-09-25 19:09:49 venglisc Exp $
#
# Update Spreadsheet provided by CIAT with PUP information
#
# $Log: not supported by cvs2svn $
#
#----------------------------------------------------------------------
import cdr, cdrdb, sys, time, cdrdocobject #, cdrcgi, 
import xml.dom.minidom, ExcelWriter, ExcelReader

if sys.platform == "win32":
    import os, msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

# -------------------------------------------------------------------
# -------------------------------------------------------------------
class PUP:
    def __init__(self, id, cursor, persRole = 'Update person'):
        self.cdrId       = id
        self.persId      = None
        self.persFname   = None
        self.persLname   = None
        self.persPhone   = None
        self.persEmail   = None
        self.persContact = None
        self.persRole    = persRole

        # Get the person name
        # -------------------
        cursor.execute("""\
          SELECT q.doc_id, u.int_val, 
                 g.value as "FName", l.value as "LName", c.value as Contact  
            FROM query_term_pub q
            JOIN query_term_pub u
              ON q.doc_id = u.doc_id
             AND u.path   = '/InScopeProtocol/ProtocolAdminInfo' +
                            '/ProtocolLeadOrg/LeadOrgPersonnel/Person/@cdr:ref'
             AND left(q.node_loc, 12) = left(u.node_loc, 12)
            JOIN query_term g
              ON u.int_val = g.doc_id
             AND g.path   = '/Person/PersonNameInformation/GivenName'
            JOIN query_term l
              ON g.doc_id = l.doc_id
             AND l.path   = '/Person/PersonNameInformation/SurName'
            JOIN query_term c
              ON g.doc_id = c.doc_id
             AND c.path   = '/Person/PersonLocations/CIPSContact'
           WHERE q.doc_id = %s
             AND q.value  = '%s'
""" % (self.cdrId, self.persRole))

        rows = cursor.fetchall()

        for row in rows:
            self.cdrId       = row[0]
            self.persId      = row[1]
            self.persFname   = row[2]
            self.persLname   = row[3]
            self.persContact = row[4]

        # Get the person's email and phone if a PUP was found
        # ---------------------------------------------------
        if self.persId:
            cursor.execute("""\
          SELECT q.doc_id, c.value, p.value, e.value
            FROM query_term q
            JOIN query_term c
              ON c.doc_id = q.doc_id
             AND c.path = '/Person/PersonLocations' +
                          '/OtherPracticeLocation/@cdr:id'
 LEFT OUTER JOIN query_term p
              ON c.doc_id = p.doc_id
             AND p.path = '/Person/PersonLocations' +
                          '/OtherPracticeLocation/SpecificPhone'
             AND LEFT(c.node_loc, 8) = LEFT(p.node_loc, 8)
 LEFT OUTER JOIN query_term e
              ON c.doc_id = e.doc_id
             AND e.path = '/Person/PersonLocations' +
                          '/OtherPracticeLocation/SpecificEmail'
             AND LEFT(c.node_loc, 8) = LEFT(e.node_loc, 8)
           WHERE q.path = '/Person/PersonLocations/CIPSContact'
             AND q.value = c.value
             AND q.doc_id = %s
""" % self.persId)

            rows = cursor.fetchall()

            for row in rows:
                self.persPhone   = row[2]
                self.persEmail   = row[3]



# -------------------------------------------------------------------
# Protocol class to identify the elements requested
# Only PUP information needs to get populated.  We're doing this by
# sending the vendor filter output through a new filter extracting 
# this information.
# -------------------------------------------------------------------
class Protocol:
    def __init__(self, protInfo, id, cursor):
        self.cdrId     = id
        self.nctId     = protInfo[u'nctId']
        self.pId       = protInfo[u'pId']
        self.phase     = protInfo[u'phase']
        self.status    = protInfo[u'status']
        self.source    = protInfo[u'source']
        self.reason    = protInfo[u'reason']
        self.pup       = PUP(self.cdrId, cursor)

        protInfo[u'pupId']      = self.pup.persId
        protInfo[u'pupFname']   = self.pup.persFname
        protInfo[u'pupLname']   = self.pup.persLname
        protInfo[u'pupContact'] = self.pup.persContact
        protInfo[u'pupPhone']   = self.pup.persPhone
        protInfo[u'pupEmail']   = self.pup.persEmail

        if not protInfo[u'pupId']:
            self.pi = PUP(self.cdrId, cursor, persRole = 'Protocol chair')

            protInfo[u'piId']      = self.pi.persId
            protInfo[u'piFname']   = self.pi.persFname
            protInfo[u'piLname']   = self.pi.persLname
            protInfo[u'piContact'] = self.pi.persContact
            protInfo[u'piPhone']   = self.pi.persPhone
            protInfo[u'piEmail']   = self.pi.persEmail


# -------------------------------------------------------------
#
# -------------------------------------------------------------
def getElementText(parent, name):
    nodes = parent.getElementsByTagName(name)
    return nodes and cdr.getTextContent(nodes[0]) or None


# -------------------------------------------------------------
# Read the protocol file 
# -------------------------------------------------------------
def readProtocols(iSheet = 0, filename = 'd:/cdr/tmp/CCR_Protocols.xls'):
    book = ExcelReader.Workbook(filename)
    sheet = book[iSheet]
    Protocols = {}
    headerRow = 1
    rownum = 0
    for row in sheet.rows:
        rownum += 1
        reason  = None
        if rownum > headerRow:
            nctId     = row[0]
            cdrId     = row[1]
            pId       = row[2]
            phase     = row[3]
            status    = row[4]
            source    = row[5]
            if iSheet == 0:
                reason = row[6]
            Protocols[cdrId.val] = {u'nctId':str(nctId),
                                    u'pId':str(pId),
                                    u'phase':str(phase),
                                    u'status':str(status),
                                    u'source':str(source),
                                    u'reason':str(reason)}
        #if rownum > 50: return Protocols
    return Protocols


# -------------------------------------------------------------
# Read the protocol file 
# -------------------------------------------------------------
def readMaster(iSheet = 3, filename = 'd:/cdr/tmp/CCR_Protocols.xls'):
    book = ExcelReader.Workbook(filename)
    sheet = book[iSheet]
    Protocols = {}
    headerRow = 1
    rownum = 0
    for row in sheet.rows:
        rownum += 1
        if rownum > headerRow:
            nctId     = row[0]
            cdrId     = row[1]
            closed    = row[2]
            completed = row[3]
            rp        = row[4]
            fda       = row[5]
            safety    = row[6]
            arms      = row[7]
            phase     = row[8]
            status    = row[9]
            source    = row[10]
            pId       = row[11]
            counter   = row[12]
            Protocols[cdrId.val] = {u'nctId':str(nctId),
                                    u'closed':str(closed),
                                    u'completed':str(completed),
                                    u'rp':str(rp),
                                    u'fda':str(fda),
                                    u'safety':str(safety),
                                    u'arms':str(arms),
                                    u'phase':str(phase),
                                    u'status':str(status),
                                    u'source':str(source),
                                    u'pId':str(pId),
                                    u'counter':str(counter)}
        #if rownum > 50: return Protocols
    return Protocols

# Excel is able to read XML files so that's what we create here
# -------------------------------------------------------------
t = time.strftime('%Y%m%d%H%M%S')
REPORTS_BASE = u'd:/cdr/tmp'

print "Running Report on BACH"
REPORTS_BASE = u'm:/cdr/tmp'

# Input file name
# ---------------
inputList = u'/CCTrials_Closed_AddPUP.xls'

# Output file name
# ----------------
name = u'/CCRTrials_Closed_with_PUP-%s.xml' % t
fullname = REPORTS_BASE + name

# ----------------------------------------------------------------------
# First Step:
# We need to read the content of the Spreadsheet provided
# ----------------------------------------------------------------------
dncProtocols = readProtocols(0, filename = REPORTS_BASE + inputList)
cccProtocols = readProtocols(1, filename = REPORTS_BASE + inputList)
phaProtocols = readProtocols(2, filename = REPORTS_BASE + inputList)
mstProtocols = readMaster(3, filename = REPORTS_BASE + inputList)

conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()

k = 0
for Protocols in [dncProtocols, cccProtocols, phaProtocols]:
    k += 1
    i = 0
    for id in Protocols.keys():
        i += 1
        print '%d-%d: Doc = %s' % (k, i, id)
        Protocol(Protocols[id], id, cursor)
        #print Protocols[id]
        #print '*****'

print 'Records processed: %s' % len(dncProtocols)
print 'Records processed: %s' % len(cccProtocols)
print 'Records processed: %s' % len(phaProtocols)
print 'Records processed: %s' % len(mstProtocols)
#sys.exit(1)
# Create the spreadsheet and define default style, etc.
# -----------------------------------------------------
wsTitle = {u'dnc':u'DO NOT CALL - LG List',
           u'ccc':u'CancerCenters 468',
           u'pha':u'Pharm 126',
           u'mst':u'Master'}
wb      = ExcelWriter.Workbook()
b       = ExcelWriter.Border()
borders = ExcelWriter.Borders(b, b, b, b)
font    = ExcelWriter.Font(name = 'Times New Roman', size = 11)
align   = ExcelWriter.Alignment('Left', 'Top', wrap = True)
style1  = wb.addStyle(alignment = align, font = font)
# style1  = wb.addStyle(alignment = align, font = font, borders = borders)
urlFont = ExcelWriter.Font('blue', None, 'Times New Roman', size = 11)
style4  = wb.addStyle(alignment = align, font = urlFont)
style2  = wb.addStyle(alignment = align, font = font, 
                         numFormat = 'YYYY-mm-dd')
alignH  = ExcelWriter.Alignment('Left', 'Bottom', wrap = True)
headFont= ExcelWriter.Font(bold=True, name = 'Times New Roman', size = 12)
boldFont= ExcelWriter.Font(bold=True, name = 'Times New Roman', size = 11)
styleH  = wb.addStyle(alignment = alignH, font = headFont)
style1b = wb.addStyle(alignment = align,  font = boldFont)
    
for key in wsTitle.keys():
    ws      = wb.addWorksheet(wsTitle[key], style1, 45, 1)
    
    # Set the colum width
    # -------------------
    if key == 'mst':
        ws.addCol( 1,  90)
        ws.addCol( 2,  55)
        ws.addCol( 3,  40)
        ws.addCol( 4,  60)
        ws.addCol( 5,  35)
        ws.addCol( 6,  35)
        ws.addCol( 7,  35)
        ws.addCol( 8,  35)
        ws.addCol( 9,  50)
        ws.addCol( 10, 100)
        ws.addCol( 11, 100)
        ws.addCol( 12, 150)
        ws.addCol( 13,  30)
    else:
        ws.addCol( 1,  90)
        ws.addCol( 2,  55)
        ws.addCol( 3,  150)
        ws.addCol( 4,  60)
        ws.addCol( 5,  80)
        ws.addCol( 6,  80)
        ws.addCol( 7,  80)
        ws.addCol( 8,  120)
        ws.addCol( 9,  120)
        ws.addCol( 10, 150)

    # Create the Header row
    # ---------------------
    if key == 'mst':
        exRow = ws.addRow(1, styleH)
        exRow.addCell(1, 'NCT-ID')
        exRow.addCell(2, 'CDR-ID')
        exRow.addCell(3, 'Closed Before 2007-09-27?')
        exRow.addCell(4, 'Completion Date')
        exRow.addCell(5, 'RP [Y/N]')
        exRow.addCell(6, 'FDA Reg [Y/N]')
        exRow.addCell(7, 'Outcome w/ Safety [Y/N]')
        exRow.addCell(8, 'Arms [Y/N]')
        exRow.addCell(9, 'Phase')
        exRow.addCell(10, 'Protocol Status')
        exRow.addCell(11, 'Source')
        exRow.addCell(12, 'Primary ID')
        exRow.addCell(13, '')
    else:
        exRow = ws.addRow(1, styleH)
        exRow.addCell(1, 'NCT-ID')
        exRow.addCell(2, 'CDR-ID')
        exRow.addCell(3, 'Primary ID')
        exRow.addCell(4, 'Phase')
        exRow.addCell(5, 'Protocols Status')
        exRow.addCell(6, 'Source')
        exRow.addCell(7, 'Reason')
        exRow.addCell(8, 'PUP/PI')
        exRow.addCell(9, 'PUP/PI Phone')
        exRow.addCell(10, 'PUP/PI Email')
        exRow.addCell(11, 'PUP/PI ID')

    # Add the protocol data one record at a time beginning after 
    # the header row
    # ----------------------------------------------------------
    rowNum = 1
    if key == 'dnc':
        Protocols = dncProtocols
    elif key == 'ccc':
        Protocols = cccProtocols
    elif key == 'pha':
        Protocols = phaProtocols
    else:
        Protocols = mstProtocols

    if key == 'mst':
        for row in Protocols.keys():
            rowNum += 1
            exRow = ws.addRow(rowNum, style1, 40)
            exRow.addCell(1, Protocols[row][u'nctId'])
            exRow.addCell(2, row)
            exRow.addCell(3, Protocols[row][u'closed'])
            exRow.addCell(4, Protocols[row][u'completed'])
            exRow.addCell(5, Protocols[row][u'rp'])
            exRow.addCell(6, Protocols[row][u'fda'])
            exRow.addCell(7, Protocols[row][u'safety'])
            exRow.addCell(8, Protocols[row][u'arms'])
            exRow.addCell(9, Protocols[row][u'phase'])
            exRow.addCell(10, Protocols[row][u'status'])
            exRow.addCell(11, Protocols[row][u'source'])
            exRow.addCell(12, Protocols[row][u'pId'])
            exRow.addCell(13, Protocols[row][u'counter'])
    else:
        for row in Protocols.keys():
            # print rowNum
            rowNum += 1
            exRow = ws.addRow(rowNum, style1, 40)
            exRow.addCell(1, Protocols[row][u'nctId'])
            exRow.addCell(2, row)
            exRow.addCell(3, Protocols[row][u'pId'])
            exRow.addCell(4, Protocols[row][u'phase'])
            exRow.addCell(5, Protocols[row][u'status'])
            exRow.addCell(6, Protocols[row][u'source'])

            if Protocols[row].has_key(u'reason') and \
               Protocols[row][u'reason']:
                exRow.addCell(7, Protocols[row][u'reason'])

            if Protocols[row].has_key(u'pupLname') and \
               Protocols[row][u'pupLname']:
                exRow.addCell(8, Protocols[row][u'pupLname'] + ", " + 
                                 Protocols[row][u'pupFname'])
            elif Protocols[row].has_key(u'piLname') and \
               Protocols[row][u'piLname']:
                exRow.addCell(8, Protocols[row][u'piLname'] + ", " + 
                                 Protocols[row][u'piFname'], style = style1b)

            if Protocols[row].has_key(u'pupPhone') and \
               Protocols[row][u'pupPhone']:
                exRow.addCell(9, Protocols[row][u'pupPhone'])
            elif Protocols[row].has_key(u'piPhone') and \
               Protocols[row][u'piPhone']:
                exRow.addCell(9, Protocols[row][u'piPhone'], style = style1b)

            if Protocols[row].has_key(u'pupEmail') and \
               Protocols[row][u'pupEmail']:
                exRow.addCell(10, Protocols[row][u'pupEmail'])
            elif Protocols[row].has_key(u'piEmail') and \
               Protocols[row][u'piEmail']:
                exRow.addCell(10, Protocols[row][u'piEmail'], style = style1b)

            if Protocols[row].has_key(u'pupId') and \
               Protocols[row][u'pupId']:
                exRow.addCell(11, Protocols[row][u'pupId'])
            elif Protocols[row].has_key(u'piId') and \
               Protocols[row][u'piId']:
                exRow.addCell(11, Protocols[row][u'piId'], style = style1b)
    
t = time.strftime("%Y%m%d%H%M%S")                                               

# # Web report
# # ----------
# print "Content-type: application/vnd.ms-excel"
# print "Content-Disposition: attachment; filename=ContentInventory-%s.xls" % t
# print  
# 
# wb.write(sys.stdout, True)

# Save the Report
# ---------------
fobj = file(fullname, "w")
wb.write(fobj)
print ""
print "  Report written to %s" % fullname
fobj.close()
