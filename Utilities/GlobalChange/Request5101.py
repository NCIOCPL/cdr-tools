# ================================================================
# Request to add a missing, mandatory GovernmentEmployee element
# for all PDQBoardMember documents.
# The element had been added for all current members but for those
# that are not current users are now receiving a DTD validation 
# error.
#                                               Volker Englisch
#                                               August 2011
#
# BZIssue::5101 - Global to add Govt Employee Element in All Board 
#                 Member Docs
#
# $Id$
#
# ================================================================
import sys, lxml.etree as lxml, ModifyDocs, cdr, cdrdb

class AddGovernmentEmployee:
    # ------------------------------------------------------
    #
    # ------------------------------------------------------
    def __init__(self, uid, pwd):
        # Save the passed name of the CDR ID file.
        # self.idFile = idFileName
        self.job    = None
        self.debug  = False
        self.session = cdr.login(uid, pwd)
        error = cdr.checkErr(self.session)
        if error:
            raise Exception("Failure logging into CDR: %s" % error)

    # ------------------------------------------------------
    # GetDocIds method that's called by ModifyDocs to identify
    # all documents to be changed.  The result has to be a list.
    # How to create the list is not important: SQL select from 
    # database, read IDs from file, have hamsters enter them
    # manually, etc.
    # ------------------------------------------------------
    def getDocIds(self):
        qry = """
          SELECT q.doc_id, q.int_val AS PersonID, fn.value AS First, 
                 ln.value AS Last, b.int_val AS BoardID, 
                 o.value AS BoardName, ge.value
            FROM query_term q
            JOIN query_term fn
              ON q.int_val = fn.doc_id
             AND fn.path   = '/Person/PersonNameInformation/GivenName'
            JOIN query_term ln
              ON q.int_val = ln.doc_id
             AND ln.path   = '/Person/PersonNameInformation/SurName'
            JOIN query_term b
              ON q.doc_id  = b.doc_id
             AND b.path    = '/PDQBoardMemberInfo/BoardMembershipDetails' +
                             '/BoardName/@cdr:ref'
            JOIN query_term o
              ON b.int_val = o.doc_id
             AND o.path    = '/Organization/OrganizationNameInformation'  +
                             '/OfficialName/Name'
left outer join query_term ge
             on q.doc_id = ge.doc_id
            and ge.path = '/PDQBoardMemberInfo/GovernmentEmployee'
           WHERE q.path    = '/PDQBoardMemberInfo/BoardMemberName/@cdr:ref'
             and ge.value is null
           ORDER BY ln.value, fn.value, o.value
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

        self.docIds = [row[0] for row in rows]

        # Debug
        # -----
        if self.debug:
            self.docIds = [369818, 369813]

        return self.docIds


    # ------------------------------------------------------
    # Run method that's called by ModifyDocs.py
    # ------------------------------------------------------
    def run(self, docObject):
        # Is the document valid before transformation?
        # --------------------------------------------
        result = cdr.valDoc(self.session, 'PDQBoardMemberInfo',
                               doc = docObject.xml)
        errBefore = cdr.getErrors(result, errorsExpected = False)
        if errBefore.find('Errors') > -1:
           valid = 'No'
        else:
           valid = 'Yes'

        print '============================================='
        self.job.log('DocValid (before): %s' % valid)
        if valid == 'No' and self.debug:
           print errBefore
           print '============================================='

        # Parse the XML
        # -------------
        tree = lxml.fromstring(docObject.xml)

        # If this is not a Board member the SELECT was wrong
        # --------------------------------------------------
        if tree.tag != 'PDQBoardMemberInfo':
            self.job.log("Doc %s is not a Board Member doc.  Check SELECT" %
                          docObject.id)
            return docObject.xml

        # Make sure the Govt Employee element doesn't already exist
        # ---------------------------------------------------------
        govtEmplElement = tree.find("GovernmentEmployee")
        if govtEmplElement is not None:
            self.job.log("Doc %s already has GovtEmpl element - skipping" %
                          docObject.id)
            return docObject.xml

        # Locate the ContactMode element.  It's required.  GovernmentEmployee
        # goes directly after it if no Affiliations exist. If Affiliations do
        # exist it goes after those.
        # -------------------------------------------------------------------
        contactModeElem = tree.xpath("./BoardMemberContactMode")
        affiliationsElem = tree.xpath("./Affiliations")

        # If we don't find exactly one ContactMode something is 
        # seriously wrong
        # -----------------------------------------------------
        if len(contactModeElem) != 1:
            self.job.log("Doc %s has %d ContactMode elements - skipping" %
                      (docObject.id, len(contactModeElem)))
            return docObject.xml

        # Create the new element text and the element
        # -------------------------------------------
        geElemText = "Unknown"
        geElem = tree.makeelement("GovernmentEmployee")
        geElem.text = geElemText

        # Append it as a sibling after ContactMode or Affiliations
        # --------------------------------------------------------
        if len(affiliationsElem) > 0:
            affiliationsElem[0].addnext(geElem)
        else:
            contactModeElem[0].addnext(geElem)

        # Return serialization of the modified document
        # ---------------------------------------------
        if self.debug:
            print '****** Updated Document ******'

        newDoc = lxml.tostring(tree)

        # Is the document valid after transformation?
        # -------------------------------------------
        result = cdr.valDoc(self.session, 'PDQBoardMemberInfo', doc = newDoc)
        errAfter = cdr.getErrors(result, errorsExpected = False)

        valid = ""
        if errAfter.find('Errors') > -1:
           valid = 'No'
        else:
           valid = 'Yes'

        self.job.log('DocValid (after):  %s' % valid)
        if valid == 'No' and self.debug:
            print errAfter
            print '=============================================\n'

        return newDoc

# -----------------------------------------------------------------
# Main program starts here
# -----------------------------------------------------------------
if __name__ == "__main__":

    if len(sys.argv) != 4:
        sys.stderr.write(
    "usage: Request5101.py userId pw live|test\n")
        sys.exit(1)

    # Get args
    # --------
    uid, pwd, runMode = sys.argv[1:]

    # Live or test mode
    # -----------------
    if runMode not in ("live", "test"):
        sys.stderr.write('Specify "live" or "test" for run mode\n')
        sys.exit(1)

    if runMode == "test":
        testMode = True
    else:
        testMode = False

    # Create the job object
    # ---------------------
    obj = AddGovernmentEmployee(uid, pwd)
    job = ModifyDocs.Job(uid, pwd, obj, obj,
          "Add the missing GovernmentEmployee element to inactive"
          " Boardmember documents, (Bug 5101)",
          validate=True, testMode=testMode)

    # So AddGovernmentEmployee obj can log
    # ------------------------------------
    obj.job = job

    # Debug
    # -----
    if obj.debug or testMode:
        job.setMaxDocs(500)

    job.run()
