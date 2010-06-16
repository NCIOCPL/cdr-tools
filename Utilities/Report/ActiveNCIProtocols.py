#----------------------------------------------------------------------
#
# $Id$
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2003/11/04 13:24:55  bkline
# New report on total active NCI-sponsored protocols for a given fiscal
# year.
#
#----------------------------------------------------------------------
import cdr, cdrdb, re, xml.dom.minidom, time, sys

class Status:
    "Protocol status for a given range of dates."
    def __init__(self, name, startDate, endDate = None):
        self.name      = name
        self.startDate = startDate
        self.endDate   = endDate

class LeadOrg:
    "Lead Organization for a protocol, with all its status history."
    def __init__(self, node):
        self.statuses = []
        self.sites    = []
        self.id       = None
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
                            self.statuses.append(Status(name, date))
            elif child.nodeName == "ProtocolSites":
                for siteNode in child.getElementsByTagName('OrgSiteID'):
                    id = siteNode.getAttribute('cdr:ref')
                    if id:
                        try:
                            digits = re.sub('[^\\d]', '', id)
                            self.sites.append(int(digits))
                        except:
                            pass
            elif child.nodeName == 'LeadOrganizationID':
                id = child.getAttribute('cdr:ref')
                if id:
                    try:
                        digits = re.sub('[^\\d]', '', id)
                        self.id = int(digits)
                    except:
                        pass
        for i in range(len(self.statuses)):
            if i == len(self.statuses) - 1:
                self.statuses[i].endDate = time.strftime("%Y-%m-%d")
            else:
                self.statuses[i].endDate = self.statuses[i + 1].startDate

class Protocol:
    "Protocol information used for an OPS report spreadsheet."
        
    def __init__(self, id, node):
        "Create a protocol object from the XML document."
        self.id       = id
        self.leadOrgs = []
        self.statuses = []

        # Collect the lead organizations into a list.
        for child in node.childNodes:
            if child.nodeName == "ProtocolAdminInfo":
                for grandchild in child.childNodes:
                    if grandchild.nodeName == "ProtocolLeadOrg":
                        self.leadOrgs.append(LeadOrg(grandchild))

        # Build sets of statuses for each start date.
        orgStatuses = []  # One for each lead org
        statuses    = {}  # Indexed by startDate
        i           = 0   # Remembers which lead org
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
            if self.statuses:
                self.statuses[-1].endDate = startDate
            self.statuses.append(Status(protStatus, startDate))
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
            if status in statusSet:
                return status
        return ""

    def wasActive(self, start, end):
        "Was this protocol active at any time during the indicated range?"
        for status in self.statuses:
            if status.endDate > start:
                if status.startDate <= end:
                    if status.name.upper() == "ACTIVE":
                        return 1
        return 0

#------------------------------------------------------------------
# Process all candidate protocols.
#------------------------------------------------------------------
if len(sys.argv) != 3:
    sys.stderr.write("usage: ActiveNCIProtocols start-date end-date\n")
    sys.stderr.write(" e.g.: ActiveNCIProtocols 2002-10-01 2003-09-30\n")
    sys.exit(1)
startDate, endDate = sys.argv[1:]
conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
cursor.execute("""\
    SELECT DISTINCT s.doc_id
               FROM query_term s
               JOIN primary_pub_doc d
                 ON d.doc_id = s.doc_id
              WHERE s.path = '/InScopeProtocol/ProtocolSponsors/SponsorName'
                AND s.value = 'NCI'
                """)
rows = cursor.fetchall()
print len(rows), "rows"
orgs       = {}
nProtocols = 0
done       = 0
for row in rows:
    cursor.execute("""\
            SELECT xml
              FROM document
             WHERE id = ?""", row[0])
    docXml = cursor.fetchone()[0]
    dom    = xml.dom.minidom.parseString(docXml.encode('utf-8'))
    prot   = Protocol(row[0], dom.documentElement)
    if prot.wasActive(startDate, endDate):
        nProtocols += 1
        for leadOrg in prot.leadOrgs:
            if leadOrg.id:
                orgs[leadOrg.id] = 1
            for site in leadOrg.sites:
                orgs[site] = 1
    done += 1
    sys.stderr.write("\rprocessed %d of %d" % (done, len(rows)))
print "\n%d active NCI-sponsored protocols" % nProtocols
print "%d unique lead and participating orgs" % len(orgs)
