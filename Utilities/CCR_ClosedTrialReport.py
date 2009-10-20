#----------------------------------------------------------------------
#
# $Id$
#
# Update Non-Compliance Report from CTGov to add PUP information.
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
# Protocol class to identify the elements requested
# Only PUP information needs to get populated.  We're doing this by
# sending the vendor filter output through a new filter extracting 
# this information.
# -------------------------------------------------------------------
class Protocol:
    def __init__(self, protInfo, id, cursor):
        self.cdrId     = id
        self.pID       = protInfo[u'pid']
        self.origTitle = u''
        self.phase     = u''
        self.respParty = u''
        self.studyCat  = []
        self.catMap    = []


        # Extract the Verification Mailer information from the database
        # -------------------------------------------------------------
        cursor.execute("""\
          SELECT d.id, i.value as "Primary ID", t.value as "Orig Title",
                 --p.value as phase, 
                 r.value as "Responsible Party" --, 
                 --s.value as "Study Category"
            FROM document d
            JOIN query_term_pub i
              ON d.id = i.doc_id
             AND i.path = '/InScopeProtocol/ProtocolIDs/PrimaryID/IDString'
            JOIN query_term_pub t
              ON d.id = t.doc_id
             AND t.path = '/InScopeProtocol/ProtocolTitle'
            JOIN query_term_pub tt
              ON d.id = tt.doc_id
             and tt.path = '/InScopeProtocol/ProtocolTitle/@Type'
             and tt.value = 'Original'
             and left(t.node_loc, 4) = left(tt.node_loc, 4)
          --  JOIN query_term_pub p
          --    on d.id = p.doc_id
          --   and p.path = '/InScopeProtocol/ProtocolPhase'
          LEFT OUTER JOIN query_term_pub r
              on d.id = r.doc_id
             and r.path like '/InScopeProtocol/RegulatoryInformation/' +
                             'ResponsibleParty/Responsible%%/@cdr:ref'
          --  JOIN query_term_pub s
          --    ON d.id = s.doc_id
          --   AND s.path = '/InScopeProtocol/ProtocolDetail/StudyCategory/' +
          --                'StudyCategoryName'
           WHERE d.id = %s
           ORDER BY d.id
""" % self.cdrId)

        rows = cursor.fetchall()

        for row in rows:
            protInfo[u'oTitle'] = row[2]
            protInfo[u'respParty'] = row[3]

        # Selecting the multiple occuring phases
        # --------------------------------------
        cursor.execute("""\
            SELECT value
              FROM query_term_pub
             WHERE path = '/InScopeProtocol/ProtocolPhase'
               AND doc_id = %s
""" % self.cdrId) 
        rows = cursor.fetchall()
        allPhases = []
        for row in rows:
            allPhases.append(row[0])

        protInfo[u'phase'] = allPhases

        # Selecting the multiple occuring StudyCategory
        # ---------------------------------------------
        cursor.execute("""\
            SELECT value
              FROM query_term_pub
             WHERE path = '/InScopeProtocol/ProtocolDetail/StudyCategory/' +
                          'StudyCategoryName'
               AND doc_id = %s
""" % self.cdrId) 
        rows = cursor.fetchall()
        allStudyNames = []
        for row in rows:
            allStudyNames.append(row[0])

        protInfo[u'studyCat'] = allStudyNames

        # Populating the Responsible Party entries
        # These can either be an Org name or a Person name
        # ------------------------------------------------
        cursor.execute("""\
          SELECT d.doc_id, o.value as "Resp Org", 
                 p.value as "Resp Person", m.value, l.value
            FROM query_term_pub d
 LEFT OUTER JOIN query_term_pub o
              ON d.int_val = o.doc_id
             AND o.path = '/Organization/OrganizationNameInformation/' + 
                          'OfficialName/Name'
 LEFT OUTER JOIN query_term_pub p
              ON d.int_val = p.doc_id
             AND p.path = '/Person/PersonNameInformation/GivenName'
 LEFT OUTER JOIN query_term_pub l
              ON d.int_val = l.doc_id
             AND l.path = '/Person/PersonNameInformation/SurName'
 LEFT OUTER JOIN query_term_pub m
              ON d.int_val = m.doc_id
             AND m.path = '/Person/PersonNameInformation/MiddleName'
           WHERE d.path like '/InScopeProtocol/RegulatoryInformation/' +
                             'ResponsibleParty/Responsible%%/@cdr:ref'
             AND d.doc_id = %s
""" % self.cdrId) 
        rows = cursor.fetchall()
        if rows:
            for cdrId, orgName, fName, mName, lName in rows:
                if orgName:
                    protInfo[u'respParty'] = orgName
                elif fName:
                    protInfo[u'respParty'] = '%s %s' % (fName, lName)
                                                        #mName and ' ' + mName,
                else:
                    protInfo[u'respParty'] = ''


        # Populating the mapped category value by extracting it from
        # the document in pub_proc_nlm
        # ------------------------------------------------
        try:
            cursor.execute("""\
              SELECT xml 
                FROM pub_proc_nlm
               WHERE id = %s
""" % self.cdrId) 
            docXml = cursor.fetchone()[0]
        except:
            print 'No document in NLM table for CDR%s' % self.cdrId
            docXml = None
            return
            
        dom = xml.dom.minidom.parseString(docXml.encode('utf-8'))

        # Setting initial variables
        # -------------------------
        catMap = None

        # Walking through the tree to find the elements available in the 
        # modified licensee output
        # --------------------------------------------------------------
        for node in dom.documentElement.childNodes:
            if node.nodeName == 'study_design':
                for child in node.childNodes:
                    if child.nodeName   == 'interventional_design':
                        for nextChild in child.childNodes:
                            if nextChild.nodeName == 'interventional_subtype':
                                catMap = cdr.getTextContent(nextChild)

            # In case we have multiple names (if we also need the information
            # for the secondary lead orgs) collect the info in a list
            # ---------------------------------------------------------------
            self.catMap = catMap

        protInfo[u'catMap'] = self.catMap



# -------------------------------------------------------------
#
# -------------------------------------------------------------
def getElementText(parent, name):
    nodes = parent.getElementsByTagName(name)
    return nodes and cdr.getTextContent(nodes[0]) or None


# -------------------------------------------------------------
# Read the protocol file 
# -------------------------------------------------------------
def readProtocols(filename = 'd:/cdr/tmp/CCR_Protocols.xls'):
    book = ExcelReader.Workbook(filename)
    sheet = book[0]
    headerRow = 1
    rownum = 0
    ccrProtocols = {}
    for row in sheet.rows:
        rownum += 1
        if rownum > headerRow:
            cdrId     = row[0]
            pID       = row[1]
            ccrProtocols[cdrId.val] = {u'pid':str(pID)}
    return ccrProtocols


# Excel is able to read XML files so that's what we create here
# -------------------------------------------------------------
wsTitle = u'CCR Closed Trials Report'
t = time.strftime('%Y%m%d%H%M%S')
REPORTS_BASE = u'd:/cdr/tmp'
REPORTS_BASE = u'm:/cdr/tmp'

# Input file name
# ---------------
inputList = u'/CCR_ClosedTrialReport.xls'

# Output file name
# ----------------
name = u'/CCR_ClosedTrialReport-%s.xml' % t
fullname = REPORTS_BASE + name

# ----------------------------------------------------------------------
# First Step:
# We need to read the content of the Spreadsheet provided
# ----------------------------------------------------------------------
ccrProtocols = readProtocols(filename = REPORTS_BASE + inputList)

conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()

i = 0
for id in ccrProtocols.keys():
    i += 1
    print '%d: Doc = %s' % (i, id)
    Protocol(ccrProtocols[id], id, cursor)
    #print ccrProtocols[id]
    #print '*****'

print 'Records processed: %s' % len(ccrProtocols)
#sys.exit(1)
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
ws      = wb.addWorksheet(wsTitle, style1, 45, 1)
style2  = wb.addStyle(alignment = align, font = font, 
                         numFormat = 'YYYY-mm-dd')
alignH  = ExcelWriter.Alignment('Left', 'Bottom', wrap = True)
headFont= ExcelWriter.Font(bold=True, name = 'Times New Roman', size = 12)
styleH  = wb.addStyle(alignment = alignH, font = headFont)
    
# Set the colum width
# -------------------
ws.addCol( 1,  55)
ws.addCol( 2,  90)
ws.addCol( 3,  500)
ws.addCol( 4,  60)
ws.addCol( 5,  80)
ws.addCol( 6,  80)
ws.addCol( 7,  80)

# Create the Header row
# ---------------------
exRow = ws.addRow(1, styleH)
exRow.addCell(1, 'CDR-ID')
exRow.addCell(2, 'Primary ID')
exRow.addCell(3, 'Original Title')
exRow.addCell(4, 'Phase')
exRow.addCell(5, 'Responsible Party')
exRow.addCell(6, 'Study Category')
exRow.addCell(7, 'Category Mapping to CTGov')

# Add the protocol data one record at a time beginning after 
# the header row
# ----------------------------------------------------------
rowNum = 1
for row in ccrProtocols.keys():
    # print rowNum
    rowNum += 1
    exRow = ws.addRow(rowNum, style1, 40)
    exRow.addCell(1, row)
    exRow.addCell(2, ccrProtocols[row][u'pid'])
    exRow.addCell(3, ccrProtocols[row][u'oTitle'])

    if ccrProtocols[row].has_key(u'phase') and \
       ccrProtocols[row][u'phase']:
        exRow.addCell(4, ", ".join([x for x in ccrProtocols[row][u'phase']]))

    exRow.addCell(5, ccrProtocols[row][u'respParty'])

    if ccrProtocols[row].has_key(u'studyCat') and \
       ccrProtocols[row][u'studyCat']:
        exRow.addCell(6, ", ".join([x for x in ccrProtocols[row][u'studyCat']]))

    if ccrProtocols[row].has_key(u'catMap') and \
       ccrProtocols[row][u'catMap']:
        exRow.addCell(7, ccrProtocols[row][u'catMap'])

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
