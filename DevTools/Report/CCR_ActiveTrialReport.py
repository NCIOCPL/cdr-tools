#----------------------------------------------------------------------
#
# $Id$
#
# Create CCR report for active and closed trials.
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
        self.pid       = protInfo[u'pid']
        self.status    = protInfo[u'status']
        self.title     = protInfo[u'title']
        self.closed    = u''
        self.phase     = u''
        self.respParty = u''
        self.studyCat  = []
        self.catMap    = []

        # Selecting the multiply occuring phases
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

        # Selecting the multiply occuring phases
        # --------------------------------------
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
def getProtocolsActive(cursor):
    protocols = {}
    try:
        cursor.execute("""\
          SELECT d.id, stat.value, s.value, i.value, nct.value, t.value 
            FROM document d
            JOIN query_term_pub s
              ON d.id = s.doc_id
             AND s.path = '/InScopeProtocol/ProtocolSources/' + 
                          'ProtocolSource/SourceName'
             AND s.value = 'NCI-CCR'
            JOIN query_term_pub stat
              ON d.id = stat.doc_id
             AND stat.path = '/InScopeProtocol/ProtocolAdminInfo/' + 
                             'CurrentProtocolStatus'
             AND stat.value in ('Active', 'Approved-not yet active', 
                                'Temporarily closed')
            JOIN query_term_pub i
              ON d.id = i.doc_id
             AND i.path = '/InScopeProtocol/ProtocolIDs/PrimaryID/IDString'
            JOIN query_term_pub t
              ON d.id = t.doc_id
             AND t.path = '/InScopeProtocol/ProtocolTitle'
            JOIN query_term_pub tt
              ON d.id = tt.doc_id
             AND tt.path = '/InScopeProtocol/ProtocolTitle/@Type'
             AND tt.value = 'Original'
             AND left(t.node_loc, 4) = left(tt.node_loc, 4)
            JOIN query_term_pub nct
              ON d.id = nct.doc_id
             AND nct.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDString'
            JOIN query_term_pub ncn
              ON d.id = ncn.doc_id
             AND left(nct.node_loc, 8) = left(ncn.node_loc, 8)
             AND ncn.value = 'ClinicalTrials.gov ID'
 LEFT OUTER JOIN query_term_pub b
              ON d.id = b.doc_id
             AND b.path = '/InScopeProtocol/BlockedFromCTGov'
           WHERE d.active_status = 'A'
             AND b.path IS NULL
           ORDER BY stat.value, d.id
""") 

        rows = cursor.fetchall()

        for cdrId, status, source, pid, nctid, title in rows:
            protocols[cdrId] = {u'pid':pid, 
                                u'nctid':nctid,
                                u'status':status,
                                u'title':title}
    except Exception, info:
        print 'Error in getProtocolsActive(): %s' % info
        return
    return protocols


# -------------------------------------------------------------
# Read the protocol file 
# -------------------------------------------------------------
def getProtocolsClosed(cursor):
    protocols = {}
    try:
        cursor.execute("""\
          SELECT d.id, stat.value, s.value, i.value, nct.value, t.value, c.value
            FROM document d
            JOIN query_term_pub s
              ON d.id = s.doc_id
             AND s.path = '/InScopeProtocol/ProtocolSources/' +
                          'ProtocolSource/SourceName'
             AND s.value = 'NCI-CCR'
            JOIN query_term_pub stat
              ON d.id = stat.doc_id
             AND stat.path = '/InScopeProtocol/ProtocolAdminInfo/' +
                             'CurrentProtocolStatus'
             AND stat.value in ('Closed', 'Completed')
            JOIN query_term_pub i
              ON d.id = i.doc_id
             AND i.path = '/InScopeProtocol/ProtocolIDs/PrimaryID/IDString'
            JOIN query_term_pub t
              ON d.id = t.doc_id
             AND t.path = '/InScopeProtocol/ProtocolTitle'
            JOIN query_term_pub tt
              ON d.id = tt.doc_id
             AND tt.path = '/InScopeProtocol/ProtocolTitle/@Type'
             AND tt.value = 'Original'
             AND left(t.node_loc, 4) = left(tt.node_loc, 4)
            JOIN query_term_pub nct
              ON d.id = nct.doc_id
             AND nct.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDString'
            JOIN query_term_pub ncn
              ON d.id = ncn.doc_id
             AND left(nct.node_loc, 8) = left(ncn.node_loc, 8)
             AND ncn.value = 'ClinicalTrials.gov ID'
      LEFT OUTER JOIN query_term_pub c
              ON d.id = c.doc_id
             AND c.path = '/InScopeProtocol/ProtocolAdminInfo/'      + 
                          'ProtocolLeadOrg/LeadOrgProtocolStatuses/' +
                          'CurrentOrgStatus/StatusDate'
      LEFT OUTER JOIN query_term_pub b
              ON d.id = b.doc_id
             AND b.path = '/InScopeProtocol/BlockedFromCTGov'
           WHERE c.value > '2007-09-27'
             AND d.active_status = 'A'
             AND b.path IS NULL
           ORDER BY stat.value, d.id
""") 

        rows = cursor.fetchall()

        for cdrId, status, source, pid, nctid, title, cDate in rows:
            protocols[cdrId] = {u'pid':pid, 
                                u'nctid':nctid,
                                u'status':status,
                                u'title':title,
                                u'closed':cDate}
    except Exception, info:
        print 'Error in getProtocolsClosed(): %s' % info
        return
    return protocols


# Excel is able to read XML files so that's what we create here
# -------------------------------------------------------------
wsTitle1 = u'CCR Active Trials Report'
wsTitle2 = u'CCR Closed Trials Report'
t = time.strftime('%Y%m%d%H%M%S')
REPORTS_BASE = u'd:/cdr/tmp'
REPORTS_BASE = 'm:/cdr/tmp'

convertCategory = ['Biomarker/Laboratory analysis',
                   'Natural history/Epidemiology',
                   'Tissue collection/Repository',
                   'Genetics']

# Input file name
# ---------------
inputList = u'/CCR_ClosedTrialReport.xls'

# Output file name
# ----------------
name = u'/CCR_ActiveTrialReport-%s.xml' % t
fullname = REPORTS_BASE + name

conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()

# ----------------------------------------------------------------------
# First Step:
# We need to read the content of the Spreadsheet provided
# ----------------------------------------------------------------------
activeProtocols = getProtocolsActive(cursor)
closedProtocols = getProtocolsClosed(cursor)

i = 0
for id in activeProtocols.keys():
    i += 1
    print '%d: Doc = %s' % (i, id)
    Protocol(activeProtocols[id], id, cursor)
    #print activeProtocols[id]
    #print '*****'

for id in closedProtocols.keys():
    i += 1
    print '%d: Doc = %s' % (i, id)
    Protocol(closedProtocols[id], id, cursor)
    #print closedProtocols[id]
    #print '*****'

print 'Records processed: %s' % len(activeProtocols)
print 'Records processed: %s' % len(closedProtocols)
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
style2  = wb.addStyle(alignment = align, font = font, 
                         numFormat = 'YYYY-mm-dd')
alignH  = ExcelWriter.Alignment('Left', 'Bottom', wrap = True)
headFont= ExcelWriter.Font(bold=True, name = 'Times New Roman', size = 12)
styleH  = wb.addStyle(alignment = alignH, font = headFont)

for wsTitle in [wsTitle1, wsTitle2]:
    if wsTitle == wsTitle1:
        Protocols = activeProtocols
    else:
        Protocols = closedProtocols

    ws      = wb.addWorksheet(wsTitle, style1, 45, 1)
    
    # Set the colum width
    # -------------------
    ws.addCol( 1,  55)
    ws.addCol( 2,  90)
    ws.addCol( 3,  90)
    ws.addCol( 4,  500)
    ws.addCol( 5,  60)
    ws.addCol( 6,  80)
    ws.addCol( 7,  80)
    ws.addCol( 8,  80)

    # Create the Header row
    # ---------------------
    exRow = ws.addRow(1, styleH)
    exRow.addCell(1, 'CDR-ID')
    exRow.addCell(2, 'PDQ Primary ID')
    exRow.addCell(3, 'NCT-ID')
    exRow.addCell(4, 'Original Title')
    exRow.addCell(5, 'Phase')
    exRow.addCell(6, 'Responsible Party')
    exRow.addCell(7, 'Study Category')
    exRow.addCell(8, 'Category Mapping to CTGov')

    # Add the protocol data one record at a time beginning after 
    # the header row
    # ----------------------------------------------------------
    rowNum = 1
    for row in Protocols.keys():
        # print rowNum
        rowNum += 1
        exRow = ws.addRow(rowNum, style1, 40)
        exRow.addCell(1, row)
        exRow.addCell(2, Protocols[row][u'pid'])
        exRow.addCell(3, Protocols[row][u'nctid'])
        exRow.addCell(4, Protocols[row][u'title'])

        if Protocols[row].has_key(u'phase') and \
           Protocols[row][u'phase']:
            exRow.addCell(5, ", ".join([x for x in Protocols[row][u'phase']]))

        if Protocols[row].has_key(u'respParty') and \
           Protocols[row][u'respParty']:
            exRow.addCell(6, Protocols[row][u'respParty'])

        if Protocols[row].has_key(u'studyCat') and \
           Protocols[row][u'studyCat']:
            exRow.addCell(7, ", ".join([x for x in Protocols[row][u'studyCat']]))

        if Protocols[row].has_key(u'catMap') and \
           Protocols[row][u'catMap']:
            exRow.addCell(8, Protocols[row][u'catMap'])
        else:
            for category in Protocols[row][u'studyCat']:
                if category in convertCategory:
                    exRow.addCell(8, 'Observational')

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
