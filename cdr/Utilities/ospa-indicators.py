#----------------------------------------------------------------------
#
# $Id: ospa-indicators.py,v 1.1 2006-08-15 14:56:37 bkline Exp $
#
# Software to export trial data to the Office of Science Policy for
# display on the Executive Dashboard.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdr, cdrdb, cPickle, sys, time, xml.dom.minidom, re, xml.sax.saxutils

termNames = {}
foundInterventions = {}
foundTrialTypes = {}
foundApprovals = {}
foundStatuses = {}
foundPhases = {}
otherCancerTypes = {}
otherInterventionTypes = {}

def fix(me):
    return me and xml.sax.saxutils.escape(unicode(me)) or u""

def quoteAttr(val):
    return u"'%s'" % fix(val).replace("'", "&apos;")

def getCcrId(cursor):
    cursor.execute("""\
        SELECT doc_id
          FROM query_term
         WHERE path = '/Organization/OrganizationNameInformation'
                    + '/OfficialName/Name'
           AND value = 'NCI - Center for Cancer Research'""")
    rows = cursor.fetchall()
    return rows and (u"CDR%010d" % rows[0][0]) or None

unwantedChars = re.compile(u"[^A-Z0-9]+")

def normalizeGrantNumber(original):
    number = unwantedChars.sub(u"", original.upper())
    caPos  = number.find(u"CA")
    if caPos == -1:
        return number
    suffix = number[caPos + 2:]
    sLen   = len(suffix)
    if sLen < 6:
        suffix = (u"000000" + suffix)[-6:]
    return u"CA%s" % suffix

def getChildrenOf(termId):
    cursor.execute("CREATE TABLE #t (id INTEGER)")
    conn.commit()
    cursor.execute("INSERT INTO #t VALUES(%d)" % termId)
    conn.commit()
    while 1:
        cursor.execute("""\
        INSERT INTO #t
             SELECT q.doc_id
               FROM query_term q
               JOIN #t t
                 ON t.id = q.int_val
              WHERE q.path = '/Term/TermRelationShip/ParentTerm' +
                             '/TermId/@cdr:ref'
                AND q.doc_id NOT IN (SELECT id FROM #t)""", timeout = 360)
        if not cursor.rowcount:
            break
        conn.commit()
    cursor.execute("SELECT id FROM #t")
    ids = [row[0] for row in cursor.fetchall()]
    cursor.execute("DROP TABLE #t")
    conn.commit()
    return ids

def loadInterventionTerms(fileName = None):
    if fileName:
        bytes = open(fileName, 'rb').read()
        return cPickle.loads(bytes)
##     cursor.execute("""\
##         SELECT doc_id, value
##           FROM query_term
##          WHERE path = '/Term/PreferredName'
##            AND value IN ('Biological therapy',
##                          'Chemotherapy',
##                          'Hormone therapy',
##                          'Radiation therapy',
##                          'Surgery')""")
    cursor.execute("""\
         SELECT t.doc_id, d.value
           FROM query_term t
           JOIN query_term d
             ON d.doc_id = t.doc_id
            AND LEFT(d.node_loc, 8) = LEFT(t.node_loc, 8)
          WHERE t.path = '/Term/MenuInformation/MenuItem/MenuType'
            AND d.path = '/Term/MenuInformation/MenuItem/DisplayName'
            AND t.value = 'Key intervention type'""")
    rows = cursor.fetchall()
    terms = {}
    for docId, name in rows:
        name = name.capitalize()
        for childId in getChildrenOf(docId):
            if childId in terms:
                terms[childId].append(name)
            else:
                terms[childId] = [name]
    #bytes = cPickle.dumps(terms)
    #fp = open('cancer-interventions.dump', 'wb')
    #fp.write(bytes)
    #fp.close()
    return terms

def loadCancerTerms(fileName = None):
    if fileName:
        bytes = open(fileName, 'rb').read()
        return cPickle.loads(bytes)
##     cursor.execute("""\
##         SELECT doc_id, value
##           FROM query_term
##          WHERE path = '/Term/PreferredName'
##            AND value IN (
##                'Bladder cancer',
##                'Breast cancer',
##                'Brain and central nervous system tumors',
##                'Cervical cancer',
##                'Colorectal cancer',
##                'Endometrial cancer',
##                'Esophageal cancer',
##                'Head and neck cancer',
##                'Kaposi''s sarcoma',
##                'Kidney cancer',
##                'Leukemia',
##                'Liver cancer',
##                'Lung cancer',
##                'Lymphoma',
##                'Melanoma (skin)',
##                'Multiple myeloma and plasma cell neoplasm',
##                'Ovarian cancer',
##                'Pancreatic cancer',
##                'Prostate cancer',
##                'Non-melanomatous skin cancer')""")
##     cursor.execute("""\
##          SELECT t.doc_id, n.value, d.value
##            FROM query_term t
##            JOIN query_term n
##              ON n.doc_id = t.doc_id
## LEFT OUTER JOIN query_term d
##              ON d.doc_id = t.doc_id
##             AND LEFT(d.node_loc, 8) = LEFT(t.node_loc, 8)
##           WHERE t.path = '/Term/MenuInformation/MenuItem/MenuType'
##             AND n.path = '/Term/PreferredName'
##             AND d.path = '/Term/MenuInformation/MenuItem/DisplayName'
##             AND t.value = 'Key cancer type'""")
    cursor.execute("""\
         SELECT t.doc_id, d.value
           FROM query_term t
           JOIN query_term d
             ON d.doc_id = t.doc_id
            AND LEFT(d.node_loc, 8) = LEFT(t.node_loc, 8)
          WHERE t.path = '/Term/MenuInformation/MenuItem/MenuType'
            AND d.path = '/Term/MenuInformation/MenuItem/DisplayName'
            AND t.value = 'Key cancer type'""")
    rows = cursor.fetchall()
    terms = {}
    for docId, name in rows:
        # name = name.capitalize()
        for childId in getChildrenOf(docId):
            if childId in terms:
                terms[childId].append(name)
            else:
                terms[childId] = [name]
    #bytes = cPickle.dumps(terms)
    #fp = open('cancer-terms.dump', 'wb')
    #fp.write(bytes)
    #fp.close()
    return terms

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

def intFromId(cdrId):
    return cdr.exNormalize(cdrId)[1]

def lookupTermName(termId):
    id = intFromId(termId)
    if id in termNames:
        return termNames[id]
    cursor.execute("""\
    SELECT value
      FROM query_term
     WHERE path = '/Term/PreferredName'
       AND doc_id = ?""", id, timeout = 300)
    rows = cursor.fetchall()
    name = rows and rows[0][0].strip() or "*** TERM CDR%d NOT FOUND ***" % id
    termNames[id] = name
    return name

class Status:
    "Protocol status for a given range of dates."
    def __init__(self, name, startDate, endDate = None):
        self.name      = name
        self.startDate = startDate
        self.endDate   = endDate

class FiscalYear:
    "Protocol status at the end of specific fiscal year"
    def __init__(self, year, yearEndStatus):
        self.year          = year
        self.yearEndStatus = yearEndStatus

class LeadOrg:

    "Lead Organization for a protocol, with all its status history."
    def __init__(self, node):
        self.statuses = []
        self.isCCR    = False
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
                            foundStatuses[name] = True
                            self.statuses.append(Status(name, date))
            elif child.nodeName == "LeadOrganizationID":
                if child.getAttribute("cdr:ref") == ccrId:
                    #sys.stderr.write("found CCR protocol\n")
                    self.isCCR = True
        self.statuses.sort(lambda a, b: cmp(a.startDate, b.startDate))
        for i in range(len(self.statuses)):
            if i == len(self.statuses) - 1:
                self.statuses[i].endDate = Protocol.today
            else:
                self.statuses[i].endDate = self.statuses[i + 1].startDate

class GrantContract:
    def __init__(self, node):
        self.contractType = u''
        self.contractNo   = u''
        for child in node.childNodes:
            if child.nodeName == 'GrantContractNo':
                self.contractNo = cdr.getTextContent(child).strip()
            elif child.nodeName == 'NIHGrantContractType':
                self.contractType = cdr.getTextContent(child).strip()

class Protocol:
    "Protocol information used for an OPS report spreadsheet."

    __okApprovalValues = {
        'NCI CTEP REVIEW': True,
        'NCI DCP REVIEW': True,
        'NCI CCR REVIEW': True,
        'NCI GRANT REVIEW': True,
        'PRMS REVIEW': True,
        'CANCER CENTER PRMS REVIEW': True
        }
    today = time.strftime("%Y-%m-%d")

    def __init__(self, id, node, startYear, endYear):
        "Create a protocol object from the XML document."
        self.id             = id
        self.leadOrgs       = []
        self.statuses       = []
        self.status         = ""
        self.firstId        = ""
        self.otherIds       = []
        self.firstPub       = ""
        self.closed         = ""
        self.completed      = ""
        self.types          = []
        self.phases         = []
        self.ageRange       = ""
        self.sponsors       = []
        self.approvals      = []
        self.interventions  = {}
        self.cancerTypes    = {}
        self.years          = []
        self.grantContracts = []
        self.title          = ""
        profTitle           = ""
        patientTitle        = ""
        originalTitle       = ""
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
                    elif grandchild.nodeName == "Diagnosis":
                        self.addCancerType(grandchild)
            elif child.nodeName == "ProtocolTitle":
                titleType = child.getAttribute("Type")
                value     = cdr.getTextContent(child)
                if value:
                    if titleType == "Professional":
                        profTitle = value
                    elif titleType == "Patient":
                        patientTitle = value
                    elif titleType == "Original":
                        originalTitle = value
            elif child.nodeName == "ProtocolAdminInfo":
                for grandchild in child.childNodes:
                    if grandchild.nodeName == "ProtocolLeadOrg":
                        leadOrg = LeadOrg(grandchild)
                        self.leadOrgs.append(leadOrg)
                        if leadOrg.isCCR:
                            self.approvals.append(u"NCI CCR review")
                    elif grandchild.nodeName == "CurrentProtocolStatus":
                        value = cdr.getTextContent(grandchild)
                        if value:
                            foundStatuses[value] = True
                            self.status = value
            elif child.nodeName == "ProtocolDetail":
                for catName in child.getElementsByTagName("StudyCategoryName"):
                    value = cdr.getTextContent(catName)
                    if value:
                        foundTrialTypes[value] = True
                        self.types.append(value)
                for intType in child.getElementsByTagName("InterventionType"):
                    self.addIntervention(intType)
                for cond in child.getElementsByTagName("Condition"):
                    self.addCancerType(cond)
            elif child.nodeName == "ProtocolApproval":
                for gc in child.childNodes:
                    if gc.nodeName == 'ReviewApprovalType':
                        approvalType = cdr.getTextContent(gc).strip()
                        if approvalType:
                            foundApprovals[approvalType] = True
                            self.approvals.append(approvalType)
            elif child.nodeName == "ProtocolPhase":
                phase = cdr.getTextContent(child).strip()
                if phase:
                    foundPhases[phase] = True
                    self.phases.append(phase)
            elif child.nodeName == "FundingInfo":
                for grandchild in child.childNodes:
                    if grandchild.nodeName == 'NIHGrantContract':
                        grantContract = GrantContract(grandchild)
                        contractNo    = grantContract.contractNo
                        if 'CA' in contractNo:
                            self.approvals.append("NCI grant review")
                            self.grantContracts.append(grantContract)
                        elif contractNo.upper().startswith('NCI'):
                            self.approvals.append("NCI grant review")

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
            self.statuses.append(Status(protStatus, startDate))
        if self.statuses:
            self.statuses[-1].endDate = Protocol.today
        self.getFiscalYearStatuses(startYear, endYear)

    def addCancerType(self, node):
        termId = node.getAttribute('cdr:ref')
        if termId:
            docId = intFromId(termId)
            if docId in cancerTerms:
                types = cancerTerms[docId]
            else:
                types = ['Other']
                name = lookupTermName(docId)
                otherType = "%s (%s)" % (termId, name)
                otherCancerTypes[otherType] = True
            for t in types:
                self.cancerTypes[t] = True

    def addIntervention(self, node):
        termId = node.getAttribute('cdr:ref')
        if termId:
            docId = intFromId(termId)
            if docId in interventionTerms:
                interventions = interventionTerms[docId]
            else:
                interventions = ['Other']
                name = lookupTermName(docId)
                otherIntervention = u"%s (%s)" % (termId, name)
                otherInterventionTypes[otherIntervention] = True
            for i in interventions:
                self.interventions[i] = True

    def getMergedPhases(self):
        if not self.phases:
            return "No phase specified"
        elif "Phase II" in self.phases:
            if "Phase I" in self.phases:
                return "Phase I/II"
            elif "Phase III" in self.phases:
                return "Phase II/III"
        return self.phases[0]

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

    def getFiscalYearStatuses(self, firstYear, lastYear):
        year = firstYear
        while year <= lastYear:
            startDate = "%d-10-01" % (year - 1)
            endDate   = "%d-09-30" % year
            if endDate > Protocol.today:
                endDate = Protocol.today
            if self.wasActive(startDate, endDate):
                status = self.getStatusForDate(endDate)
                self.years.append(FiscalYear(year, status))
            year += 1
                
    def getStatusForDate(self, date):
        #sys.stderr.write("date=%s\n" % date)
        status = None
        for s in self.statuses:
            #sys.stderr.write("s.startDate=%s\n" % s.startDate)
            #sys.stderr.write("s.endDate=%s\n" % s.endDate)
            if s.startDate > date:
                return status
            if s.startDate <= date and s.endDate >= date:
                status = s.name
        return status
        
    def wasActive(self, start, end):
        "Was this protocol active at any time during the indicated range?"
        for status in self.statuses:
            if status.endDate > start:
                if status.startDate <= end:
                    if status.name.upper() in ("ACTIVE",
                                               "APPROVED-NOT YET ACTIVE"
                                               ):
                        return 1
        return 0

    def toXml(self):
        lines = [u"""\
 <Trial DocId='CDR%010d' PDQPrimaryProtocolId=%s>""" % (self.id,
                                                 quoteAttr(self.firstId))]
        for y in self.years:
            s = y.yearEndStatus
            if s == 'Approved-not yet active':
                s = 'Approved - not yet active'
            lines.append(u"  <Status FiscalYear='%d'>%s</Status>" %
                         (y.year, fix(y.yearEndStatus)))
        if self.title:
            lines.append(u"  <Title>%s</Title>" % fix(self.title))
        url = ("http://www.cancer.gov/clinicaltrials/"
               "view_clinicaltrials.aspx?version=healthprofessional&amp;"
               "cdrid=%d" % self.id)
        lines.append(u"  <Link>%s</Link>" % url)
        p = self.getMergedPhases()
        lines.append(u"  <Phase>%s</Phase>" % p)
        types = self.cancerTypes.keys()
        types.sort()
        if "Other" in types:
            types.remove('Other')
            types.append('Other')
        for t in types:
            lines.append(u"  <CancerType>%s</CancerType>" % t)
        for t in self.types:
            lines.append(u"  <TrialType>%s</TrialType>" % t)
        if u"Treatment" in self.types:
            interventions = self.interventions.keys()
            interventions.sort()
            if "Other" in interventions:
                interventions.remove('Other')
                if not interventions:
                    interventions.append('Other')
            for i in interventions:
                lines.append(u"  <Intervention>%s</Intervention>" % fix(i))
        approvals = self.__filterApprovals()
        for a in approvals:
            lines.append(u"  <NCIApprovedReview>%s</NCIApprovedReview>" %
                         fix(a))
        for g in self.grantContracts:
            lines.append(u"""\
  <NIHGrantContract>
   <NIHGrantContractType>%s</NIHGrantContractType>
   <GrantContractNo>%s</GrantContractNo>
  </NIHGrantContract>""" % (fix(g.contractType),
                            fix(normalizeGrantNumber(g.contractNo))))
        lines.append(u" </Trial>")
        return lines

    def __filterApprovals(self):
        approvals = []
        other     = False
        for approval in self.approvals:
            ucApproval = approval.upper()
            if ucApproval == 'PRMS REVIEW':
                ucApproval = 'CANCER CENTER PRMS REVIEW'
                approval = 'Cancer Center PRMS review'
            if ucApproval in self.__okApprovalValues:
                if approval not in approvals:
                    approvals.append(approval)
            else:
                other = True
        if other and not approvals:
            approvals = [u'Other']
        return approvals

startYear         = len(sys.argv) > 1 and int(sys.argv[1]) or 2001
endYear           = len(sys.argv) > 2 and int(sys.argv[2]) or 2006
maxTrials         = len(sys.argv) > 3 and int(sys.argv[3]) or 500000
fileName          = len(sys.argv) > 4 and sys.argv[4]      or None
intervFileName    = len(sys.argv) > 5 and sys.argv[5]      or None
conn              = cdrdb.connect('CdrGuest')
cursor            = conn.cursor()
ccrId             = getCcrId(cursor)
numTrials         = 0
numParsed         = 0
start             = time.time()
cancerTerms       = loadCancerTerms(fileName)
interventionTerms = loadInterventionTerms(intervFileName)
sys.stderr.write("CCR ID is %s\n" % ccrId)
cursor.execute("""\
    SELECT DISTINCT v.id, MAX(v.num)
               FROM doc_version v
               JOIN query_term s
                 ON v.id = s.doc_id
               JOIN document d
                 ON d.id = v.id
              WHERE d.active_status = 'A'
                AND v.publishable = 'Y'
                AND s.path = '/InScopeProtocol/ProtocolSponsors/SponsorName'
                AND s.value = 'NCI'
           GROUP BY v.id""", timeout = 300)
rows = cursor.fetchall()
stamp = time.strftime("%Y-%m-%dT%H:%M:%S")
lines = [u"<Trials ExtractionDateTime='%s'>" % stamp]
for row in rows:
    cursor.execute("""\
        SELECT xml
          FROM doc_version
         WHERE id = ?
           AND num = ?""", row)
    docXml = cursor.fetchone()[0]
    dom = xml.dom.minidom.parseString(docXml.encode('utf-8'))
    prot = Protocol(row[0], dom.documentElement, startYear, endYear)
    numParsed += 1
    if prot.years:
        lines += prot.toXml()
        numTrials += 1
    now = time.time()
    timer = getElapsed(start, now)
    sys.stderr.write("\rparsed %d of %d trials, exported %d (%s)" % (numParsed,
                                                                     len(rows),
                                                                     numTrials,
                                                                     timer))
    if numTrials >= maxTrials:
        break
lines.append(u"</Trials>\n")
name = time.strftime("ospa-%Y%m%d.xml")
xmlFile = file(name, 'w')
xmlFilewrite((u"\n".join(lines)).encode('utf-8'))
xmlFile.close()

## def writeValues(f, name, dict):
##     keys = dict.keys()
##     keys.sort()
##     f.write('FOUND %s\n' % name)
##     for k in keys:
##         f.write("\t%s\n" % k)
##     f.write('\n')

## f = open('ospa-found-values.txt', 'w')
## f.write("%d trials parsed\n" % numParsed)
## f.write("%d trials exported\n" % numTrials)
## writeValues(f, 'INTERVENTIONS', foundInterventions)
## writeValues(f, 'TRIAL TYPES', foundTrialTypes)
## writeValues(f, 'APPROVALS', foundApprovals)
## writeValues(f, 'STATUSES', foundStatuses)
## writeValues(f, 'PHASES', foundPhases)
## writeValues(f, 'OTHER CANCER TYPES', otherCancerTypes)
## writeValues(f, 'OTHER INTERVENTION TYPES', otherInterventionTypes)
## f.close()
