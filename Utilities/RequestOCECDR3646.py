#----------------------------------------------------------------
# $Id$
#
# Global change the current status for abandoned InScopeProtocols.
#
# Parameters:
#   UserID, password, mode ('test' or 'live'), maxDocs
#
# BZIssue::OCECDR-3646
#
#                                           Alan Meyer
#                                           May, 2013
#----------------------------------------------------------------
import sys, datetime, lxml.etree as et, cdr, cdrdb, ModifyDocs

class OneOffGlobal:
    """
    All code for this transformation is here.
    """

    def __init__(self):
        """
        Create any variables needed throughout processing.
        """
        # Current date
        now = datetime.datetime.now()
        self.curDate = ("%4d-%02d-%02d" % (now.year, now.month, now.day))

        # These will be initialized by the main program
        self.userId = None
        self.jobId  = None

    def log(self, docId, msg, skip=False):
        """
        Log a message pertaining to a document.

        Pass:
            docId - CDR ID of the InScopeProtocol
            msg   - Text of the message to log
            skip  - True = we've skipped this document
        """
        if not docId:
            docId = 'None'
        if not hpId:
            hpId = 'None'
        logMsg = "Doc ID=%s: %s" % (docId, msg)
        if skip:
            logMsg += ", no changes made"

        # Use the ModifyDocs log function to put this message in context
        self.job.log(logMsg)

    def getDocIds(self):

        # Find all InScopeProtocols that have been abandoned and
        #  have an Active or Approved-not yet active
        # Picks up both English and Spanish
        qry = """
    SELECT q.doc_id
      FROM query_term_pub q
      -- Uncomment if we want to limit to docs currently on cancer.gov
      -- JOIN pub_proc_cg c
      -- ON c.id = q.doc_id
      JOIN query_term_pub s
        ON q.doc_id = s.doc_id
     WHERE q.path = '/InScopeProtocol/CTGovOwnershipTransferContactLog/CTGovOwnershipTransferContactResponse'
       AND q.value = 'Abandoned'
       AND s.path = '/InScopeProtocol/ProtocolAdminInfo/CurrentProtocolStatus'
       AND s.value IN ('Active', 'Approved-not yet active')
     ORDER BY q.doc_id
"""
        try:
            conn = cdrdb.connect()
            cursor = conn.cursor()
            cursor.execute(qry)
            rows = cursor.fetchall()
            cursor.close()
        except cdrdb.Error as info:
            self.job.log("Database error selecting ids: %s" % str(info))
            sys.exit(1)

        # Save and return them
        self.docIds = [row[0] for row in rows]
        return self.docIds

    def run(self, docObj):

        # Parse the Patient Summary xml
        tree = et.fromstring(docObj.xml)

        # Check the overall current status of the doc
        overallStat = tree.xpath(
              "/InScopeProtocol/ProtocolAdminInfo/CurrentProtocolStatus")

        # If status already unknown, we're done with this doc
        # Makes this safe to run multiple times
        if overallStat[0].tag == "Unknown":
            self.log(docObj.id,
                     "CurrentProtocolStatus already set to Unknown", True)
            # Return unchanged xml
            return docObj.xml

        # Process each lead organization
        leadOrgs = tree.xpath(
            "/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg")

        # There has to be one or it's a mangled document
        if len(leadOrgs) == 0:
            self.log(docObj.id, "No lead orgs in this doc - can't happen", True)
            return docObj.xml

        # Process each one
        for leadOrg in leadOrgs:
            statuses   = leadOrg.find("LeadOrgProtocolStatuses")
            curOrgStat = statuses.find("CurrentOrgStatus")
            statName   = curOrgStat.find("StatusName")
            if statName is None:
                # Missing required field, should never happen
                self.log(docObj.id,
                    "No StatusName found in LeadOrg - Can't happen!", True);
                return docObj.xml

            if statName.text == "Unknown":
                # Don't modify this lead org, it's already Unknown status
                continue

            # Copy all of the current status info to a new PreviousOrgStatus
            curStatChildren = curOrgStat.getchildren()
            newPrevStat = et.Element("PreviousOrgStatus")
            for child in curStatChildren:
                # Documentation of deepcopy is inadequate.  arg is unused?
                newPrevStat.append(child.__deepcopy__(None))

            # Create a new current status element to replace the existing one
            newCurStat = et.Element("CurrentOrgStatus")

            newSubElement = et.Element("StatusName")
            newSubElement.text = "Unknown"
            newCurStat.append(newSubElement)

            newSubElement = et.Element("StatusDate")
            newSubElement.text = self.curDate
            newCurStat.append(newSubElement)

            newSubElement = et.Element("Comment")
            newSubElement.text = \
                    "Added by global change for JIRA task OCECDR-3646"
            newCurStat.append(newSubElement)

            newSubElement = et.Element("EnteredBy")
            newSubElement.text = self.userId
            newCurStat.append(newSubElement)

            newSubElement = et.Element("EntryDate")
            newSubElement.text = self.curDate
            newCurStat.append(newSubElement)

            # Replaces the current org status
            statuses.replace(curOrgStat, newCurStat)

            # New element goes after current org status
            #  but before first previous stat
            newCurStat.addnext(newPrevStat)

        newXml = et.tostring(tree)

        return newXml


if __name__ == "__main__":
    if len(sys.argv) < 4 or sys.argv[3] not in ('test', 'live'):
        sys.stderr.write("usage: JIRA-OCEDIR-3646.py uid pwd test|live")
        sys.exit(1)
    uid, pwd, flag = sys.argv[1:4]

    # Boolean true = test, false = live
    testMode = (flag == 'test')

    # Debug
    # testMode = True

    obj = OneOffGlobal()
    try:
        job = ModifyDocs.Job(uid, pwd, obj, obj,
                'Set the protocol status to "Unknown" for abandoned trials',
                validate=True, testMode=testMode)
    except Exception, info:
        sys.stderr.write("Exception: %s" % str(info))
        sys.exit(1)
    except:
        sys.stderr.write("An exception occurred")
        sys.exit(1)

    # Store reference to the job object in the object passed to Job.
    # This makes logging and credentials available to the logic
    obj.job = job

    # Make the user ID available for inclusion in the EnteredBy status element
    obj.userId = uid

    # Debug
    # job.setMaxDocs(50)

    job.run()
    try:
        # job.run()
        pass
    except Exception, info:
        sys.stderr.write("Exception: %s" % str(info))
        sys.exit(1)
    except:
        sys.stderr.write("An exception occurred")
