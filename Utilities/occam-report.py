#----------------------------------------------------------------------
#
# $Id$
#
# Report for Office of Cancer Complementary and Alternative Medicine (OCCAM).
#
# "The Office of Cancer Complementary and Alternative Medicine needs a report
# similar to the special Office of Science Policy report that we generate. The
# report, in Excel format will be in the same format as the OSP report for
# cancer types. The criteria for selction for this report though is not
# eligible diagnoses or condition, but InterventionType. Bob and I discussed
# this report yesterday.
#
# Criteria
#
# NCI sponsored trials that were active at any point in FY 2005 that have
# 'complementary and alternative therapy (42022)' as the InterventionType
# (either directly or as a parent of an InterventionType term). Could you also
# add Phase to the standard Excel report format."
#
# BZIssue::2502
# BZIssue::2869
# BZIssue::4182
# BZIssue::4610
#
#----------------------------------------------------------------------
import cdr, cdrdb, xml.dom.minidom, time, sys, ExcelWriter, re

#----------------------------------------------------------------------
# Create a string showing delta between two times.
#----------------------------------------------------------------------
def getElapsed(then, now):
    delta = now - then
    secs = delta % 60
    delta /= 60
    mins = delta % 60
    hours = delta / 60
    return "%02d:%02d:%02d" % (hours, mins, secs)

class ProtocolStatus:
    "Protocol status for a given range of dates."
    def __init__(self, name, startDate, endDate = None):
        self.name      = name
        self.startDate = startDate
        self.endDate   = endDate

class LeadOrg:
    "Lead Organization for a protocol, with all its status history."
    def __init__(self, node):
        self.statuses = []
        for child in node.childNodes:
            if child.nodeName == "LeadOrgProtocolStatuses":
                for grandchild in child.childNodes:
                    if grandchild.nodeName in ("PreviousOrgStatus",
                                               "CurrentOrgStatus"):
                        name = ""
                        date = ""
                        for greatgrandchild in grandchild.childNodes:
                            if greatgrandchild.nodeName == "StatusDate":
                                date = cdr.getTextContent(greatgrandchild)
                            elif greatgrandchild.nodeName == "StatusName":
                                name = cdr.getTextContent(greatgrandchild)
                        if name and date:
                            self.statuses.append(ProtocolStatus(name, date))
        self.statuses.sort(lambda a, b: cmp(a.startDate, b.startDate))
        for i in range(len(self.statuses)):
            if i == len(self.statuses) - 1:
                self.statuses[i].endDate = time.strftime("%Y-%m-%d")
            else:
                self.statuses[i].endDate = self.statuses[i + 1].startDate

class Objectives:
    elementTypes = {}
    def __init__(self, node):
        self.node = node
    def toHtml(self):
        f = """\
<xsl:transform           xmlns:xsl = "http://www.w3.org/1999/XSL/Transform"
                           version = "1.0"
                         xmlns:cdr = "cips.nci.nih.gov/cdr">
 <xsl:output                method = "html"/>
 <xsl:include  href = "cdr:name:Module: Inline Markup Formatter"/>
</xsl:transform>
"""
        t = "<Objectives xmlns:cdr='cips.nci.nih.gov/cdr'"
        s = self.node.toxml('utf-8').replace("<Objectives",  t)
        r = cdr.filterDoc('guest', f, doc = s, inline = True)
        cdr.logwrite("Objectives:\n%s" % s, LOGFILE)
        if type(r) in (unicode, str):
            return u"<span style='color:red'>Filter failure: %s</span>" % r
        cdr.logwrite("HTML:\n%s" % r[0], LOGFILE)
        return unicode(r[0], 'utf-8')
        
    
class Protocol:
    "Protocol information used for OPS-like reports."

    def __init__(self, id, node, getObjectives = False):
        "Create a protocol object from the XML document."
        self.id         = id
        self.leadOrgs   = []
        self.statuses   = []
        self.status     = ""
        self.firstId    = ""
        self.otherIds   = []
        self.firstPub   = ""
        self.closed     = ""
        self.completed  = ""
        self.types      = []
        self.ageRange   = ""
        self.sponsors   = []
        self.title      = ""
        self.origTitle  = ""
        self.phases     = []
        self.objectives = None
        profTitle       = ""
        patientTitle    = ""
        originalTitle   = ""
        for child in node.childNodes:
            if child.nodeName == "ProtocolSponsors":
                for grandchild in child.childNodes:
                    if grandchild.nodeName == "SponsorName":
                        value = cdr.getTextContent(grandchild)
                        if value:
                            self.sponsors.append(value)
            elif child.nodeName == "ProtocolIDs":
                for grandchild in child.childNodes:
                    if grandchild.nodeName == "PrimaryID":
                        for greatgrandchild in grandchild.childNodes:
                            if greatgrandchild.nodeName == "IDString":
                                value = cdr.getTextContent(greatgrandchild)
                                self.firstId = value
                    if grandchild.nodeName == "OtherID":
                        for greatgrandchild in grandchild.childNodes:
                            if greatgrandchild.nodeName == "IDString":
                                value = cdr.getTextContent(greatgrandchild)
                                if value:
                                    self.otherIds.append(value)
            elif child.nodeName == "Eligibility":
                for grandchild in child.childNodes:
                    if grandchild.nodeName == "AgeText":
                        value = cdr.getTextContent(grandchild)
                        if value:
                            self.ageRange = value
            elif child.nodeName == "ProtocolTitle":
                titleType = child.getAttribute("Type")
                value     = cdr.getTextContent(child)
                if value:
                    if titleType == "Professional":
                        profTitle = value
                    elif titleType == "Patient":
                        patientTitle = value
                    elif titleType == "Original":
                        originalTitle = self.origTitle = value
            elif child.nodeName == "ProtocolAdminInfo":
                for grandchild in child.childNodes:
                    if grandchild.nodeName == "ProtocolLeadOrg":
                        self.leadOrgs.append(LeadOrg(grandchild))
                    elif grandchild.nodeName == "CurrentProtocolStatus":
                        value = cdr.getTextContent(grandchild)
                        if value:
                            self.status = value
            elif child.nodeName == "ProtocolDetail":
                for catName in child.getElementsByTagName(
                                                     "StudyCategoryName"):
                    value = cdr.getTextContent(catName)
                    if value:
                        self.types.append(value)
            elif child.nodeName == 'ProtocolPhase':
                self.phases.append(cdr.getTextContent(child))
            elif getObjectives and child.nodeName == "ProtocolAbstract":
                for grandchild in child.childNodes:
                    if grandchild.nodeName == "Professional":
                        for o in grandchild.childNodes:
                            if o.nodeName == "Objectives":
                                self.objectives = Objectives(o)
        if profTitle:
            self.title = profTitle
        elif originalTitle:
            self.title = originalTitle
        elif patientTitle:
            self.title = patientTitle
        orgStatuses = []
        statuses    = {}
        i           = 0
        for leadOrg in self.leadOrgs:
            orgStatuses.append("")
            for orgStatus in leadOrg.statuses:
                startDate = orgStatus.startDate
                val = (i, orgStatus.name)
                statuses.setdefault(startDate, []).append(val)
            i += 1
        keys = statuses.keys()
        keys.sort()
        for startDate in keys:
            for i, orgStatus in statuses[startDate]:
                orgStatuses[i] = orgStatus
            protStatus = self.getProtStatus(orgStatuses)
            if protStatus == "Active" and not self.firstPub:
                self.firstPub = startDate
            if protStatus in ("Active", "Approved-not yet active",
                              "Temporarily closed"):
                self.closed = ""
            elif not self.closed:
                self.closed = startDate
            if protStatus == 'Completed':
                self.completed = startDate
            else:
                self.completed = ""
            if self.statuses:
                self.statuses[-1].endDate = startDate
            self.statuses.append(ProtocolStatus(protStatus, startDate))
        if self.statuses:
            self.statuses[-1].endDate = time.strftime("%Y-%m-%d")

    def getProtStatus(self, orgStatuses):
        "Look up the protocol status based on the status of the lead orgs."
        statusSet = {}
        for orgStatus in orgStatuses:
            key = orgStatus.upper()
            statusSet[key] = 1 + statusSet.get(key, 0)
        if len(statusSet) == 1:
            return orgStatuses[0]
        for status in ("Active",
                       "Temporarily closed",
                       "Completed",
                       "Closed",
                       "Approved-not yet active"):
            if status.upper() in statusSet:
                return status
        return ""

    def wasActive(self, start, end):
        "Was this protocol active at any time during the indicated range?"
        for status in self.statuses:
            if status.endDate > start:
                if status.startDate <= end:
                    if status.name.upper() in ("ACTIVE",
                                               #"APPROVED-NOT YET ACTIVE"
                                               ):
                        return 1
        return 0

def request2502(startDate, endDate):

    start = time.time()
    
    try:
        conn = cdrdb.connect('CdrGuest')
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE #terms(id INTEGER)")
        conn.commit()
        cursor.execute("INSERT INTO #terms VALUES(42022)")
        conn.commit()
        while True:
            cursor.execute("""\
        INSERT INTO #terms
             SELECT q.doc_id
               FROM query_term q
               JOIN #terms t
                 ON t.id = q.int_val
              WHERE q.path = '/Term/TermRelationShip/ParentTerm' +
                             '/TermId/@cdr:ref'
                AND q.doc_id NOT IN (SELECT id FROM #terms)""", timeout = 360)
            if not cursor.rowcount:
                break
            conn.commit()
        
        cursor.execute("""\
                 SELECT DISTINCT t.doc_id, MAX(v.num)
                   FROM query_term t
                   JOIN query_term s
                     ON s.doc_id = t.doc_id
                   JOIN document d
                     ON d.id = s.doc_id
                   JOIN doc_version v
                     ON v.id = d.id
                  WHERE t.path = '/InScopeProtocol/ProtocolDetail'
                               + '/StudyCategory/Intervention'
                               + '/InterventionType/@cdr:ref'
                    AND t.int_val IN (SELECT id FROM #terms)
                    AND s.path = '/InScopeProtocol/ProtocolSponsors' +
                                 '/SponsorName'
                    AND s.value = 'NCI'
                    AND d.active_status = 'A'
                    AND v.publishable = 'Y'
               GROUP BY t.doc_id
               ORDER BY t.doc_id""", timeout = 360)
        rows = cursor.fetchall()
    except Exception, e:
        sys.stderr.write("Database failure getting list of protocols: %s\n"
                         % e)
        raise

    # Create the spreadsheet.
    wb = ExcelWriter.Workbook()
    b = ExcelWriter.Border()
    borders = ExcelWriter.Borders(b, b, b, b)
    font = ExcelWriter.Font(name = 'Times New Roman', size = 10)
    align = ExcelWriter.Alignment('Left', 'Top', wrap = True)
    style1 = wb.addStyle(alignment = align, font = font, borders = borders)
    urlFont = ExcelWriter.Font('blue', None, 'Times New Roman', size = 10)
    style4 = wb.addStyle(alignment = align, font = urlFont, borders = borders)
    ws = wb.addWorksheet("PDQ Clinical Trials", style1, 40, 1)
    style2 = wb.addStyle(alignment = align, font = font, borders = borders,
                         numFormat = 'YYYY-mm-dd')
    
    # Set the column widths to match the sample provided by OSP.
    ws.addCol( 1, 232.5)
    ws.addCol( 2, 100)
    ws.addCol( 3, 127.5)
    ws.addCol( 4, 104.25)
    ws.addCol( 5, 104.25)
    ws.addCol( 6, 104.25)
    ws.addCol( 7, 91.5)
    ws.addCol( 8, 84.75)
    ws.addCol( 9, 85.5)
    ws.addCol(10, 123)
    ws.addCol(11, 100)

    # Set up the header cells in the spreadsheet's top row.
    font = ExcelWriter.Font(name = 'Times New Roman', bold = True, size = 10)
    align = ExcelWriter.Alignment('Center', 'Center', wrap = True)
    interior = ExcelWriter.Interior('#CCFFCC')
    style3 = wb.addStyle(alignment = align, font = font, borders = borders,
                         interior = interior)
    row = ws.addRow(1, style3, 40)
    headings = (
        'PDQ Clinical Trials',
        'Primary ID',
        'Additional IDs',
        'Date First Activated',
        'Date Moved to Closed List',
        'Date Completed',
        'Current Status',
        'Type of Trial',
        'Age Range',
        'Sponsor of Trial',
        'Phase(s)'
        )
    for i in range(len(headings)):
        row.addCell(i + 1, headings[i])

    #------------------------------------------------------------------
    # Process all candidate protocols.
    #------------------------------------------------------------------
    done      = 0
    protocols = []
    for row in rows:
        cursor.execute("""\
            SELECT xml
              FROM doc_version
             WHERE id = ?
               AND num = ?""", row)
        docXml = cursor.fetchone()[0]
        dom = xml.dom.minidom.parseString(docXml.encode('utf-8'))
        prot = Protocol(row[0], dom.documentElement)
        if prot.wasActive(startDate, endDate):
            protocols.append(prot)
        done += 1
        now = time.time()
        timer = getElapsed(start, now)
        msg = "Processed %d of %d protocols; elapsed: %s" % (done,
                                                             len(rows),
                                                             timer)
        sys.stderr.write(msg + "\n")

    # Add one row for each protocol.
    rowNum = 1
    protocols.sort(lambda a,b: cmp(a.firstPub, b.firstPub))
    for prot in protocols:

        # Change requested by Lakshmi 2005-02-25 (request #1567).
        if prot.status in ('Closed', 'Completed'):
            closedDate = prot.closed
            if prot.status == 'Completed':
                completedDate = prot.completed
            else:
                completedDate = ''
        else:
            closedDate = ''
            completedDate = ''

        rowNum += 1
        row = ws.addRow(rowNum, style1, 40)
        tip = ("Left-click cell with mouse to view the protocol document.  "
               "Left-click and hold to select the cell.")
        url = ("http://www.cancer.gov/clinicaltrials/"
               "view_clinicaltrials.aspx?version=healthprofessional&"
               "cdrid=%d" % prot.id)
        row.addCell(1, prot.title)
        row.addCell(2, prot.firstId, href = url, tooltip = tip, style = style4)
        row.addCell(3, "; ".join(prot.otherIds))
        row.addCell(4, prot.firstPub, style = style2)
        row.addCell(5, closedDate, style = style2)
        row.addCell(6, completedDate, style = style2)
        row.addCell(7, prot.status)
        row.addCell(8, "; ". join(prot.types))
        row.addCell(9, prot.ageRange)
        row.addCell(10, "; ".join(prot.sponsors))
        row.addCell(11, "; ".join(prot.phases))
        row = cursor.fetchone()

    # Save the report.
    # name = "Request4610.xls" # "Request4182.xls" #"Request2869.xls"
    now  = time.strftime("%Y%m%d")
    name = "occam-report-%s.xls" % now
    fobj = file(name, "wb")
    wb.write(fobj, True)
    fobj.close()
    print "wrote", name

def usage():
    sys.stderr.write("usage: %s start-date end-date\n")
    sys.stderr.write(" (dates must be in ISO format)\n")
    sys.stderr.write("e.g.: %s 2007-10-01 2008-09-30\n")
    sys.exit(1)

def checkDateArg(arg):
    if len(arg) != 10 or not re.match(r"\d\d\d\d-\d\d-\d\d", arg):
        return False
    return True
if len(sys.argv) != 3:
    usage()
if not checkDateArg(sys.argv[1]) or not checkDateArg(sys.argv[2]):
    usage()
request2502(sys.argv[1], sys.argv[2])
