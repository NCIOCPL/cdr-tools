#----------------------------------------------------------------------
#
# $Id$
#
# List of CTEP and DCP active trials for CTRP.
#
#----------------------------------------------------------------------
import cdrdb, time, sys, lxml.etree as etree

class ProtocolStatusHistory:
    """
    Represents laboriously assembled evolution of an InScopeProtocol's
    overall status.
    """

    activeStatuses = set(['Active', 'Approved-not yet active'])
    statusPrecedence = ('Active', 'Temporarily closed', 'Closed',
                        'Approved-not yet active')

    class Status:
        "Protocol status for a given range of dates."
        def __init__(self, status, startDate = None):
            self.endDate = None
            if isinstance(status, basestring):
                self.name = status
                self.startDate = startDate
            else:
                self.name = self.startDate = None
                for child in status:
                    if child.tag == 'StatusName':
                        self.name = child.text
                    elif child.tag == 'StatusDate':
                        self.startDate = child.text
        def __cmp__(self, other):
            diff = cmp(self.startDate, other.startDate)
            if diff:
                return diff
            return cmp(self.endDate, other.endDate)

    class LeadOrg:
        "Lead organization for a protocol, with all its status history"
        statusTags = set(['PreviousOrgStatus', 'CurrentOrgStatus'])
        def __init__(self, node):
            self.statuses = []
            for child in node.findall('LeadOrgProtocolStatuses'):
                for grandchild in child:
                    if grandchild.tag in self.statusTags:
                        status = ProtocolStatusHistory.Status(grandchild)
                        if status.name and status.startDate:
                            self.statuses.append(status)
            self.statuses.sort()
            for i, status in enumerate(self.statuses):
                if i == len(self.statuses) - 1:
                    status.endDate = time.strftime("%Y-%m-%d")
                else:
                    status.endDate = self.statuses[i + 1].startDate

    def __init__(self, doc):
        """
        This is a moderately tricky piece of code.  We're trying to assemble
        the information we need in order to answer the question "What was
        the status of this protocol at any given point in time?"  In order
        to do this we must first assemble the sequence of status values
        each lead organization had for the protocol every time the
        organization changed that value.  Then we assemble all of the
        unique dates on which any of the organizations changed its
        status value for the protocol.  Then we need to determine, for
        each of those dates, what the status value was for each of
        the lead organizations.  We do this be creating an array of
        status value strings, one string for each lead organization
        found in the protocol document.  We initialize each string
        in the array to an empty string, and the string for a given
        lead organization will remain empty until the first date on
        which a value was found associated with that organization.
        Then for each date we apply the logic for determining what
        the overall status value for the protocol is based on the
        combinations of values held by the lead organizations at that
        point in time.  See the getProtocolStatus() method for a
        description of this logic.

        The constructor accepts either a parsed XML tree object
        (as created by the lxml.etree package) or a Unicode or
        utf-8 string serialization of the CDR InScopeProtocol
        document.
        """

        #-------------------------------------------------------------------
        # Parse the document if that hasn't already been done.
        #-------------------------------------------------------------------
        if type(doc) is str:
            tree = etree.XML(doc)
        elif type(doc) is unicode:
            tree = etree.XML(doc.encode('utf-8'))
        else:
            tree = doc

        #-------------------------------------------------------------------
        # Assemble a sequence of the lead organization histories for the trial.
        #-------------------------------------------------------------------
        leadOrgs = []
        for node in tree.findall('ProtocolAdminInfo/ProtocolLeadOrg'):
            leadOrgs.append(ProtocolStatusHistory.LeadOrg(node))

        #-------------------------------------------------------------------
        # Create a dictionary of the unique dates on which one or more
        # lead organizations changed its status for the protocol.  The
        # keys for the dictionary are the strings for these dates.  The
        # values are lists of tuples with the index position of the lead 
        # org in the leadOrgs array and the status the lead org assigned 
        # to the protocol on the date for this list of tuples.
        #-------------------------------------------------------------------
        statusesByDate = {}
        for i, leadOrg in enumerate(leadOrgs):
            for orgStatus in leadOrg.statuses:
                val = (i, orgStatus.name)
                statusesByDate.setdefault(orgStatus.startDate, []).append(val)
        startDates = statusesByDate.keys()
        startDates.sort()

        #-------------------------------------------------------------------
        # Create an array of status values, one for each lead organization.
        # We will simulate a walk through time, updating the the values
        # in this array at each point in time when one or more lead org
        # changed its status for the protocol, and then determining what
        # the overall status was at that point in time for the protocol.
        # As we go along, the start date for each node in the array except
        # the first is used as the end date for the previous node in the
        # array.
        #-------------------------------------------------------------------
        orgStatuses = [''] * len(leadOrgs)
        self.statuses = []
        for startDate in startDates:
            for i, orgStatus in statusesByDate[startDate]:
                orgStatuses[i] = orgStatus
            protStatus = ProtocolStatusHistory.getProtocolStatus(orgStatuses)
            if self.statuses:
                self.statuses[-1].endDate = startDate
            self.statuses.append(self.Status(protStatus, startDate))

        #-------------------------------------------------------------------
        # Fill in the endDate member of the protocol's last Status object.
        #-------------------------------------------------------------------
        if self.statuses:
            self.statuses[-1].endDate = time.strftime("%Y-%m-%d")

    def hadStatus(self, statusSet, startDate, endDate = '2099-12-31'):
        """
        Answers the question "Did this protocol ever have any of the
        specified statuses at any time between a specified range of
        dates?"
        """
        for status in self.statuses:
            if status.endDate >= startDate:
                if status.startDate <= endDate:
                    if status.name in statusSet:
                        return True
        return False

    def wasActive(self, startDate, endDate = '2099-12-31'):
        return self.hadStatus(self.activeStatuses, startDate, endDate)

    @staticmethod
    def getProtocolStatus(statuses):
        """
        If all of the lead organizations have the same status value for
        a protocol on a given date, then that value is used as the overall
        status for the protocol.  Otherwise a prioritized list of values
        is tested in order, and the first value in that list which is
        present for any of the lead organizations is used as the value
        for the protocol's overall status.  If none of the values in the
        prioritized list is found, then an empty string is returned.
        """
        statusSet = set([s.upper() for s in statuses])
        if len(statusSet) == 1:
            return statuses[0]
        for value in ProtocolStatusHistory.statusPrecedence:
            if value.upper() in statusSet:
                return value
        return ""

class Trial:
    def __init__(self, docId, tree):
        self.docId = docId
        self.ctepId = self.dcpId = self.nctId = None
        for node in tree.findall('ProtocolIDs/OtherID'):
            idString = idType = None
            for child in node:
                if child.tag == 'IDType':
                    idType = child.text.strip().upper()
                elif child.tag == 'IDString':
                    idString = child.text.strip()
            if idType == 'CTEP ID':
                self.ctepId = idString
            elif idType == 'DCP ID':
                self.dcpId = idString
            elif idType == 'CLINICALTRIALS.GOV ID':
                self.nctId = idString

def fix(me):
    if not me:
        return ""
    return me.encode('utf-8')

def main():
    cursor = cdrdb.connect('CdrGuest').cursor()
    cursor.execute("""\
        SELECT DISTINCT doc_id
                   FROM query_term
                  WHERE path = '/InScopeProtocol/ProtocolSources'
                             + '/ProtocolSource/SourceName'
                    AND value IN ('NCI-CTEP', 'NCI-DCP')""", timeout=300)
    docIds = [row[0] for row in cursor.fetchall()]
    done = 0
    active = []
    for docId in docIds:
        cursor.execute("SELECT xml FROM document WHERE id = ?", docId)
        docXml = cursor.fetchall()[0][0]
        tree = etree.XML(docXml.encode('utf-8'))
        statuses = ProtocolStatusHistory(tree)
        if statuses.wasActive('2009-01-01'):
            active.append(Trial(docId, tree))
        done += 1
        sys.stderr.write("\rprocessed %d of %d trials; %d matches" %
                         (done, len(docIds), len(active)))
    print "CDR ID\tCTEP ID\tDCP ID\tNCT ID"
    for trial in active:
        print "%s\t%s\t%s\t%s" % (trial.docId, fix(trial.ctepId),
                                  fix(trial.dcpId), fix(trial.nctId))

if __name__ == '__main__':
    main()
