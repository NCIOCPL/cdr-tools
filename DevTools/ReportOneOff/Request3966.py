#----------------------------------------------------------------------
#
# $Id$
#
# Match Grant Numbers against Protocols
#
# "We need to match the grant numbers in the spreadsheet (match on string
# starting CA xxxxx- ignore characters before and after) to trials and group
# them by status
#
# ie Grant Number Princpal Investigators Institution  PDQ Active Trials    PDQ
# Closed Trials
#
# I need this report to prepare for a meeting for the Central Clinical Trials
# Database.
#
# Let me know if you have questions. I will attach the spreadsheet with the 
# next coment."
#
# [Comment #1]
# "Add two columns to the spreadsheet. PDQ Active Trials PDQ Closed Trials
# and report numbers. We want to make sure that we only have trials that are
# not blocked. 
#
# Active = Active and Active Not Yet Approved
# Closed = Closed, Completed, Temporarily Closed
#
# If there are Withdrawn trials, we may need to add another column.
#
# BZIssue::3966
#
#----------------------------------------------------------------------
import ExcelReader, ExcelWriter, cdrdb, re, sys

pattern = re.compile(".*(CA\\d+).*")
inScopeContractNumbers = {}
ctGovContractNumbers = {}
statuses = {}
protocolStatuses = {}
def isActive(docId):
    if docId not in protocolStatuses:
        cursor.execute("""\
            SELECT value
              FROM query_term
             WHERE doc_id = ?
               AND path = '/InScopeProtocol/ProtocolAdminInfo'
                        + '/CurrentProtocolStatus'""", docId)
        rows = cursor.fetchall()
        if not rows:
            sys.stderr.write("*** CAN'T FIND STATUS FOR CDR%d ***\n" % docId)
            protocolStatuses[docId] = None
        else:
            protocolStatuses[docId] = rows[0][0].strip().lower()
    status = protocolStatuses[docId]
    if not status:
        return True # per Lakshmi
    return protocolStatuses[docId] in ('active', 'approved-not yet active')
def isClosed(docId):
    status = protocolStatuses[docId]
    if status in ('closed', 'completed', 'temporarily closed'):
        return True
    return False
def isWithdrawn(docId):
    if protocolStatuses[docId] == 'withdrawn':
        return True
    return False
def hasNoStatus(docId):
    status = protocolStatuses[docId]
    if not status:
        return True
    sys.stderr.write("*** STATUS FOR CDR%d IS '%s' ***\n" % (docId, status))
def normalize(value):
    value = value.strip().upper()
    ca = value.find('CA')
    if ca == -1:
        return None
    value = value[ca + 2:].strip()
    digits = []
    for c in value:
        if c.isdigit():
            digits.append(c)
        elif not c.isspace():
            if c != '-' or digits:
                break
    if not digits:
        return None
    val = int("".join(digits))
    return "CA%d" % val

cursor = cdrdb.connect('CdrGuest').cursor()
cursor.execute("""\
    SELECT q.doc_id, q.value
      FROM query_term q
      JOIN active_doc a
        ON a.id = q.doc_id
     WHERE q.path = '/InScopeProtocol/FundingInfo/NIHGrantContract'
                  + '/GrantContractNo'
       AND q.value LIKE '%CA%'""")
for docId, contractId in cursor.fetchall():
    contractId = normalize(contractId)
    if contractId:
        if contractId not in inScopeContractNumbers:
            inScopeContractNumbers[contractId] = set()
        inScopeContractNumbers[contractId].add(docId)
print "collected %d in scope contract numbers" % len(inScopeContractNumbers)
cursor.execute("""\
    SELECT doc_id, value
      FROM query_term
     WHERE path IN ('/CTGovProtocol/IDInfo/OrgStudyID',
                    '/CTGovProtocol/IDInfo/SecondaryID')""")
for docId, values in cursor.fetchall():
    for value in re.split(u"[;,]", values):
        contractId = normalize(value)
        if contractId:
            if contractId not in ctGovContractNumbers:
                ctGovContractNumbers[contractId] = set()
            ctGovContractNumbers[contractId].add(docId)
print "collected %d ctgov contract numbers" % len(ctGovContractNumbers)
book = ExcelReader.Workbook('Clinical-Trials-Grants-Coded-FY2007.xls')
sheet = book[0]
grants = []
for row in sheet:
    originalGrantNumber = row[0].val
    match = pattern.match(originalGrantNumber)
    if match:
        grantNumber = normalize(match.group(1))
        print grantNumber
        principalInvestigator = row[1].val.strip()
        institution = row[2].val.strip()
        grants.append((grantNumber, principalInvestigator, institution,
                       originalGrantNumber.strip()))
print "collected %d grants" % len(grants)
book = ExcelWriter.Workbook()
sheet = book.addWorksheet('Grants')
row = sheet.addRow(1)
row.addCell(1, 'FY2007 CLINICAL TRIALS GRANTS')
row = sheet.addRow(2)
row.addCell(1, 'Grant Number')
row.addCell(2, 'Principal Investigator')
row.addCell(3, 'Institution')
row.addCell(4, 'PDQ Grant Number')
row.addCell(5, 'PDQ Active Trials')
row.addCell(6, 'PDQ Closed Trials')
row.addCell(7, 'Withdrawn Trials')
row.addCell(8, 'CT.gov Trials')
rowNumber = 3
for number, pi, org, originalNumber in grants:
    activeTrials    = 0
    closedTrials    = 0
    ctGovTrials     = 0
    withdrawnTrials = 0
    if number in inScopeContractNumbers:
        for docId in inScopeContractNumbers[number]:
            if isActive(docId):
                activeTrials += 1
            elif isClosed(docId):
                closedTrials += 1
            elif isWithdrawn(docId):
                withdrawnTrials += 1
    if number in ctGovContractNumbers:
        for docId in ctGovContractNumbers[number]:
            ctGovTrials += 1
    row = sheet.addRow(rowNumber)
    rowNumber += 1
    row.addCell(1, originalNumber)
    row.addCell(2, pi)
    row.addCell(3, org)
    row.addCell(4, number)
    row.addCell(5, activeTrials, 'Number')
    row.addCell(6, closedTrials, 'Number')
    row.addCell(7, withdrawnTrials, 'Number')
    row.addCell(8, ctGovTrials, 'Number')
fp = open('Request3966.xls', 'wb')
book.write(fp, True)
fp.close()
