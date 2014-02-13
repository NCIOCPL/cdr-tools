#----------------------------------------------------------------------
#
# $Id$
#
# "Pancreatic Cancer Trials CDRID
#
# I am attaching a list of CDRIDs (some Inscope and some CTGOV) for which we
# need a report that has some fields from the standard OSPA Spreadsheet that
# we generate
#
# CDRID Title Primary ID Additional IDs Type of Trial Phase PI Name Expected
#                                                                   Enrollment
#
# PI name in Inscope Protocols will be from LeadOrgPersonnel/Person where the
# sibling PersonRole has one of the values - Protocol Chair, Protocol Co-chair,
# Principal Investigator
#
# PI name for CTGOV Protocols will be from OverallOfficial.
# 
# Let me know if you have questions. Would appreciate getting the report by
# Monday.
#
# BZIssue::4878
#
#----------------------------------------------------------------------
import cdrdb, sys, ExcelReader, ExcelWriter, lxml.etree as etree

class Trial:
    def __init__(self, cdrId, cursor):
        self.cdrId = cdrId
        self.title = None
        self.primaryId = None
        self.otherIds = []
        self.trialTypes = []
        self.phases = []
        self.piNames = []
        self.expectedEnrollment = None
        cursor.execute("SELECT xml FROM document WHERE id = ?", cdrId)
        docXml = cursor.fetchall()[0][0]
        tree = etree.XML(docXml.encode('utf-8'))
        self.docType = tree.tag
        if self.docType == 'InScopeProtocol':
            for node in tree.findall('ProtocolTitle[@Type="Professional"]'):
                self.title = node.text.strip()
            for node in tree.findall('ProtocolIDs'):
                for child in node.findall('PrimaryID/IDString'):
                    self.primaryId = child.text.strip()
                for child in node.findall('OtherID/IDString'):
                    self.otherIds.append(child.text.strip())
            for node in tree.findall('ProtocolDetail/StudyCategory'):
                categoryName = categoryType = None
                for child in node:
                    if child.tag == 'StudyCategoryType':
                        categoryType = child.text
                    elif child.tag == 'StudyCategoryName':
                        categoryName = child.text
                if categoryName and categoryType =='Primary':
                    self.trialTypes.append(categoryName.strip())
            for node in tree.findall('ProtocolPhase'):
                self.phases.append(node.text.strip())
            for node in tree.findall('ProtocolAdminInfo/ProtocolLeadOrg'):
                for child in node.findall('LeadOrgPersonnel'):
                    for role in child.findall('PersonRole'):
                        if role.text.upper() in ('PROTOCOL CHAIR',
                                                 'PROTOCOL CO-CHAIR',
                                                 'PRINCIPAL INVESTIGATOR'):
                            for person in child.findall('Person'):
                                name = person.text.split('[')[0].strip()
                                self.piNames.append(name)
            for node in tree.findall('ExpectedEnrollment'):
                self.expectedEnrollment = node.text
        else:
            for node in tree.findall('OfficialTitle'):
                self.title = node.text.strip()
            for node in tree.findall('IDInfo'):
                for child in node.findall('OrgStudyID'):
                    self.primaryId = child.text.strip()
                for child in node.findall('NCTID'):
                    self.otherIds.append(child.text.strip())
                for child in node.findall('SecondaryID'):
                    self.otherIds.append(child.text.strip())
            for node in tree.findall('PDQIndexing/StudyCategory'):
                categoryName = categoryType = None
                for child in node:
                    if child.tag == 'StudyCategoryType':
                        categoryType = child.text
                    elif child.tag == 'StudyCategoryName':
                        categoryName = child.text
                if categoryName and categoryType =='Primary':
                    self.trialTypes.append(categoryName)
            for node in tree.findall('Phase'):
                self.phases.append(node.text.strip())
            for node in tree.findall('Sponsors/OverallOfficial/Surname'):
                self.piNames.append(node.text.strip())
            for node in tree.findall('CTGovIndexing/CTExpectedEnrollment'):
                self.expectedEnrollment = node.text.strip()
def main():

    # Collect the document IDs for the trials to be reported.
    book = ExcelReader.Workbook(sys.argv[1])
    sheet = book[0]
    docIds = [int(row[0].val) for row in sheet]

    # Create the spreadsheet (cloned from OSP report in CdrLongReports.py).
    title = "Clinical Trials for Pancreatic Cancer"
    wb = ExcelWriter.Workbook()
    b = ExcelWriter.Border()
    borders = ExcelWriter.Borders(b, b, b, b)
    font = ExcelWriter.Font(name = 'Times New Roman', size = 10)
    align = ExcelWriter.Alignment('Left', 'Top', wrap = True)
    style1 = wb.addStyle(alignment = align, font = font, borders = borders)
    urlFont = ExcelWriter.Font('blue', None, 'Times New Roman', size = 10)
    style2 = wb.addStyle(alignment = align, font = urlFont, borders = borders)
    ws = wb.addWorksheet("PDQ Clinical Trials", style1, 40, 2)
    
    ws.addCol(1, 50)
    ws.addCol(2, 250)
    ws.addCol(3, 100)
    ws.addCol(4, 125)
    ws.addCol(5, 85)
    ws.addCol(6, 85)
    ws.addCol(7, 100)
    ws.addCol(8, 100)

    # Set up the title and header cells in the spreadsheet's top rows.
    font = ExcelWriter.Font(name = 'Times New Roman', bold = True, size = 10)
    align = ExcelWriter.Alignment('Center', 'Center', wrap = True)
    interior = ExcelWriter.Interior('#CCFFCC')
    style3 = wb.addStyle(alignment = align, font = font, borders = borders,
                         interior = interior)
    headings = ('CDRID', 'Title', 'Primary ID', 'Additional IDs',
                 'Type of Trial', 'Phase', 'PI Name', 'Expected Enrollment')
    row = ws.addRow(1, style3, 40)
    row.addCell(1, title, mergeAcross = len(headings) - 1)
    row = ws.addRow(2, style3, 40)
    for i in range(len(headings)):
        row.addCell(i + 1, headings[i])

    cursor = cdrdb.connect('CdrGuest').cursor()
    rowNum = 3
    for docId in docIds:
        trial = Trial(docId, cursor)
        row = ws.addRow(rowNum, style1, 40)
        tip = ("Left-click cell with mouse to view the protocol document.  "
               "Left-click and hold to select the cell.")
        url = ("http://www.cancer.gov/clinicaltrials/"
               "view_clinicaltrials.aspx?version=healthprofessional&"
               "cdrid=%d" % trial.cdrId)
        row.addCell(1, trial.cdrId)
        row.addCell(2, trial.title)
        row.addCell(3, trial.primaryId, href = url, tooltip = tip,
                    style = style2)
        row.addCell(4, u"; ".join(trial.otherIds))
        row.addCell(5, u"; ".join(trial.trialTypes))
        row.addCell(6, u"; ".join(trial.phases))
        row.addCell(7, u"; ".join(trial.piNames) or u"NOT SPECIFIED")
        row.addCell(8, trial.expectedEnrollment)
        rowNum += 1
    fp = open('d:/tmp/Request4878.xls', 'wb')
    wb.write(fp, True)
    fp.close()
if __name__ == '__main__':
    main()
