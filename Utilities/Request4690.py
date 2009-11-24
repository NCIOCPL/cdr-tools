#----------------------------------------------------------------------
# $Id$
#
# Global change to add various elements from InScopeProtocols to
# corresponding CTGovProtocols after a transfer of responsibility
#
# BZIssue::4690
#----------------------------------------------------------------------
import sys, cdr, cdrdb, ModifyDocs

etree = cdr.importEtree()

# Name of the program for logging
SCRIPT = "Request4690.py"

# Queries to find the documents we need
DOCS_WITH_SAME_CDRID = """
-- Find protocols transferred with the newer technique that assigns
--   the CTGovProtocol to the same CDR ID as the earlier CTGovProtocol
-- Retrieves the CDR ID and the version number of the last InScopeProtocol
--   before the first CTGovProtocol replacement.
    SELECT v.id, MAX(v.num)
      FROM doc_version v
      JOIN doc_type t
        ON t.id = v.doc_type
      JOIN (SELECT v.id, MIN(v.num) AS first_version
              FROM doc_version v
              JOIN doc_type t
                ON t.id = v.doc_type
             WHERE t.name = 'CTGovProtocol'
             GROUP BY v.id) AS c
        ON c.id = v.id
     WHERE t.name = 'InScopeProtocol'
       AND v.num < c.first_version
  GROUP BY v.id
  ORDER BY v.id
"""

DOCS_WITH_NEW_CDRID = """
-- Finds CDR IDs of InScopeProtocols and successor CTGovProtocols where
--   the successor documents were given new CDR IDs (an older technique)
-- Retrieves two CDR IDs, but no version numbers.  The InScopeProtocols
--   that we want should all be the current working documents.
  SELECT CTGovQ.doc_id, InScopeQ.doc_id
    FROM query_term InScopeQ
    JOIN query_term NctIdQ
      ON InScopeQ.doc_id = NctIdQ.doc_id
     AND LEFT(InScopeQ.node_loc, 8) = LEFT(NctIdQ.node_loc, 8)
    JOIN query_term CTGovQ
      ON CTGovQ.value = InScopeQ.value
    JOIN all_docs d
      ON InScopeQ.doc_id = d.id
   WHERE InScopeQ.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDString'
     AND NctIdQ.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
     AND NctIdQ.value = 'ClinicalTrials.gov ID'
     AND CTGovQ.path = '/CTGovProtocol/IDInfo/NCTID'
     AND d.active_status = 'I'
     -- Following will work if we index the required path
     -- Otherwise, no harm done
     AND CTGovQ.doc_id NOT IN (
        SELECT doneQ.doc_id
          FROM query_term doneQ
         WHERE doneQ.path = '/CTGovProtocol/PDQProtocolIDs/PrimaryID'
         )
   ORDER BY CTGovQ.doc_id
"""

DOCS_WITH_MAGNUSON_CENTER = """
-- Finds all CTGovProtocols with Facility links to the NIH Magnuson center.
-- Most or all of these will be in the above two result sets but if any are
--   not we'll inspect them too to see if they need SpecialCategory
--   element additions.
-- Use of CDR IDs for the link targets has been discussed and deemed proper
--   for this application.
  SELECT doc_id
    FROM query_term
   WHERE path='/CTGovProtocol/Location/Facility/Name/@cdr:ref'
     AND int_val in (34517, 32457)
   ORDER BY doc_id
"""

#----------------------------------------------------------------------
# Determine whether the clinical center at the main NIH campus is
# (or is about to be) actively participating in this trial.
# See Request #4689.
# -- Copied from Bob's ImportCTGovProtocols.py for one-off use.
#----------------------------------------------------------------------
def hasActiveMagnusonSite(tree):
    for node in tree.findall('Location'):
        facility = status = None
        for child in node.iterchildren():
            if child.tag == 'Facility':
                for grandchild in child.findall('Name'):
                    facility = grandchild.get("{cips.nci.nih.gov/cdr}ref")
            elif child.tag == 'Status':
                status = child.text
        if facility in (u'CDR0000034517', u'CDR0000032457'):
            if status in (u'Active', u'Temporarily closed'): #u'Approved-not yet active'):
                return True
    return False


def insertElement(parent, child, position):
    """
    Insert a subelement at a specific position, incrementing the position.
    Produces one element per line.

    Pass:
        parent   - Parent element node.
        child    - Node to insert.
        position - Insert subelement here among other parent's children

    Return:
        Updated position.
    """
    parent.insert(position, child)
    child.tail = "\n "
    return position + 1


def addAdminElems(oldAdmin, newAdmin, tag, position, data):
    """
    Add subelements to the new PDQAdminInfo element.

    If the tag names one or more elements that exist in the oldAdmin, copy
    the element(s) to the new version.

    If not, but we have data to insert (from the old InScopeProtocol document)
    add that instead.

    Pass:
        oldAdmin  - old PDQAdminInfo element in the CTGov doc.
                    This will None when working with CTGov docs that were
                    never InScope.
        newAdmin  - new PDQAdminInfo element we're building to replace it.
        tag       - tag of Element to copy or create.
        position  - ordinal position within the parent.
        data      - data to insert.  May be None.

    Return:
        Void.
    """
    if oldAdmin is not None:
        # Find and copy whatever is already there
        elems = oldAdmin.findall(tag)
        if len(elems):
            for elem in elems:
                position = insertElement(newAdmin, elem, position)

        # Else put in new data
        elif data:
            position = insertElement(newAdmin, data, position)

    # Or put in new
    elif data is not None:
        position = insertElement(newAdmin, data, position)

    return position


def createMagnusonElem():
    """
    Create an Element to hold the NIH Clinical Center trial SpecialCategory.

    Return:
        new element.
    """
    # Create element with our special category
    bigCat   = etree.Element("ProtocolSpecialCategory")
    smallCat = etree.SubElement(bigCat, "SpecialCategory")
    comment  = etree.SubElement(bigCat, "Comment")

    # Add text and formatting
    bigCat.text   = " \n  "
    smallCat.text = "NIH Clinical Center trial"
    smallCat.tail = "\n"
    bigCat.tail   = " \n  "
    comment.text  = "Inserted by global change"
    comment.tail  = "\n"

    # Return the whole thing
    return bigCat


class ProtDoc:
    """
    Holds information we need to locate one protocol pair.
    """
    def __init__(self, ctgovId, inscopeId=None, vernum=None):
        self.ctgovCdrId    = ctgovId
        self.inscopeCdrId  = inscopeId
        self.inscopeVerNum = vernum


def fatal(msg):
    """
    Log an error and abort.
    """
    # To default debug.log
    cdr.logwrite("%s: %s" % (SCRIPT, msg))
    # Abort
    sys.exit(1)


class FilterTransform:

    def __init__(self):
        # One connection for all queries
        try:
            self.conn = cdrdb.connect('cdr')
            # Default is off, but this just confirms that
            self.conn.setAutoCommit(on=False)
        except cdrdb.Error, info:
            fatal ("Unable to connect to database: %s" % info)

        # Store the protocol doc ids here
        self.protDocs = {}

    def getDocIds(self):
        """
        Get all the doc IDs and version numbers we need.
        Store them.
        Return just the CTGovProtocol IDs.  We'll get the rest of the
        stuff when we need it.
        """
        # Docs in which the InScope doc was replaced by CTGov with same ID
        cursor = self.conn.cursor()
        try:
            cursor.execute(DOCS_WITH_SAME_CDRID)
            rows = cursor.fetchall()
            cursor.close()
        except cdrdb.Error, info:
            fatal("Unable to select documents with same IDs:\n%s" % info)
        # DEBUG
        print("DOCS_WITH_SAME_CDRID returned %d rows" % len(rows))

        # Store each one
        for row in rows:
            # Same CDR IDs plus version number
            oneProtocol = ProtDoc(row[0], row[0], row[1])
            self.protDocs[row[0]] = oneProtocol

        # Docs in which the InScope doc was replaced by CTGov with new ID
        cursor = self.conn.cursor()
        try:
            cursor.execute(DOCS_WITH_NEW_CDRID)
            rows = cursor.fetchall()
            cursor.close()
        except cdrdb.Error, info:
            fatal("Unable to select documents with new IDs:\n%s" % info)
        # DEBUG
        print("DOCS_WITH_NEW_CDRID returned %d rows" % len(rows))

        # Store each one
        for row in rows:
            # Different CDR IDs, no version number
            oneProtocol = ProtDoc(row[0], row[1])
            self.protDocs[row[0]] = oneProtocol

        # All CTGov docs that have links to the Magnuson Center
        cursor = self.conn.cursor()
        try:
            cursor.execute(DOCS_WITH_MAGNUSON_CENTER)
            rows = cursor.fetchall()
            cursor.close()
        except cdrdb.Error, info:
            fatal("Unable to select Magnuson documents:\n%s" % info)
        # DEBUG
        print("DOCS_WITH_MAGNUSON returned %d rows" % len(rows))

        # Store only those we don't already have
        for row in rows:
            if not self.protDocs.has_key(row[0]):
                # No InScope ID, no version, these are all pure CTGov docs
                oneProtocol = ProtDoc(row[0])
                self.protDocs[row[0]] = oneProtocol

        # Return a sorted list
        keys = self.protDocs.keys()
        keys.sort()
        # DEBUG
        print("Total docs = %d" % len(keys))

        return keys


    def run(self, ctgovDocObj):
        """
        Transform one doc.

        Pass:
            Doc object for CTGovProtocol to be transformed.

        Any InScopeProtocol document needed will be retrieved here.
        """
        # Get the document ID and XML
        ctgovId  = cdr.exNormalize(ctgovDocObj.id)[1]
        ctgovXml = ctgovDocObj.xml

        # It is possible that an older version of the import program
        #   got a CTGov doc and updated the last InScope version to include
        #   the NCTID.  In that case, ModifyDocs could hand us an InScope
        #   doc when it gives us the last version or last pub version to
        #   transform.
        # If that happens, just return it to ModifyDocs, which will see
        #   there is no change and do nothing with it.
        if ctgovDocObj.type != "CTGovProtocol":
            return ctgovXml

        # Produce an ElementTree
        try:
            ctgovTree = etree.fromstring(ctgovXml)
        except Exception, info:
            fatal("Error parsing CTGovProtocol:\n%s\n" % info)

        # DEBUG
        print("Processing CTGov CDR ID=%d" % ctgovId)

        # Find associated InScope information, if any
        inscopeId = None
        if self.protDocs.has_key(ctgovId):
            protDoc   = self.protDocs[ctgovId]
            inscopeId = protDoc.inscopeCdrId
            # DEBUG
            print("InScope CDR ID=%s  version=%s" % (inscopeId,
                  protDoc.inscopeVerNum))

        # Default values for what needs to be added
        needPDQAdminInfo = False
        needMagnusonInfo = False
        fundingInfo      = None
        ownerTransLog    = None
        ownerTransInfo   = None
        pdqProtocolIDs   = None

        # If there is a corresponding InScope document
        if inscopeId:
            # Fetch either versioned doc or CWD
            if protDoc.inscopeVerNum:
                version = protDoc.inscopeVerNum
            else:
                version = "Current"
            inscopeDocObj = cdr.getDoc('guest', inscopeId, version=version,
                                        getObject=True)
            if type(inscopeDocObj) == type(""):
                fatal("Error fetching CDR doc %d: %s" % (inscopeId,
                                                         inscopeDocObj))

            # Parse the InScope document
            inscopeXml = inscopeDocObj.xml
            try:
                inscopeTree = etree.fromstring(inscopeXml)
            except Exception, info:
                fatal("Error parsing InScopeProtocol:\n%s\n" % info)

            # Get the parts we might need
            fundingInfo    = inscopeTree.find(
                                "FundingInfo")
            ownerTransLog  = inscopeTree.find(
                                "CTGovOwnershipTransferContactLog")
            ownerTransInfo = inscopeTree.find(
                                "CTGovOwnershipTransferInfo")
            protocolIDs    = inscopeTree.find(
                                "ProtocolIDs")

            # ProtocolIDs have several complications:
            #  1. They may have been inserted using an earlier schema in what
            #     is now the wrong place.  If so, we have to keep these but
            #     Move them to the right place.
            #  2. If taken from the InScopeProtocol, they require a change
            #     of element tag from "ProtocolIDs" to "PDQProtocolIDs".
            # In either case, if there is an existing
            #   CTGovProtocol/PDQAdminInfo/PDQProtocolIDs,
            #   we'll use that one.
            oldIDs = ctgovTree.find("PDQProtocolIDs")
            if oldIDs is not None:
                # We have case 1
                # Use oldIDs as the source, not the InScopeProtocol
                pdqProtocolIDs = oldIDs

                # Delete them from the CTGovProtocol, they'll go in again
                #   later if they are needed.
                # ElementTree does the right thing here keeping oldIDs alive
                #   while removing it from the CTGov tree.
                ctgovTree.remove(oldIDs)

            elif protocolIDs is not None:
                # We have case 2 above
                # Recreate the element with the new tag
                pdqProtocolIDs = etree.Element("PDQProtocolIDs")
                position = 0
                for elem in protocolIDs.getchildren():
                    insertElement(pdqProtocolIDs, elem, position)
                    position += 1

            # If we got anything, we'll need a PDQAdminInfo block for them
            if fundingInfo is not None or ownerTransLog is not None or \
                    ownerTransInfo is not None or protocolIDs is not None:
                needPDQAdminInfo = True
            # DEBUG
            print(
           "fundingInfo:%s trLog:%s trInfo:%s protocolIDs:%s oldIDs:%s" %
                   (fundingInfo is not None, ownerTransLog is not None,
                    ownerTransInfo is not None, protocolIDs is not None,
                    oldIDs is not None))

        # Whether or not we have an InScope doc, we might need SpecialCategory
        if hasActiveMagnusonSite(ctgovTree):
            needMagnusonInfo = True
            needPDQAdminInfo = True
            # DEBUG
            print("needPDQAdminInfo=%s  needMagnusonInfo=%s" %
                   (needPDQAdminInfo, needMagnusonInfo))

        if not needPDQAdminInfo:
            # We're done, just return the original doc without change
            return ctgovXml

        # Do we already have PDQAdminInfo
        oldAdminElem = ctgovTree.find("PDQAdminInfo")

        # Create a new one
        newAdminElem = etree.Element("PDQAdminInfo")

        # Add a bit of formatting
        newAdminElem.text = "\n"
        newAdminElem.tail = "\n"

        # Move all the elements from the CTGov or the InScope doc
        position = 0
        position = addAdminElems(oldAdminElem, newAdminElem, "PDQProtocolIDs",
                      position, pdqProtocolIDs)

        position = addAdminElems(oldAdminElem, newAdminElem, "FundingInfo",
                   position, fundingInfo)

        position = addAdminElems(oldAdminElem, newAdminElem,
                   "CTGovOwnershipTransferContactLog", position, ownerTransLog)

        position = addAdminElems(oldAdminElem, newAdminElem,
                   "CTGovOwnershipTransferInfo", position, ownerTransInfo)

        # For SpecialCategory, have to look at contents
        if oldAdminElem is not None:
            cats = oldAdminElem.findall("ProtocolSpecialCategory")
            for elem in cats:
                if elem.findtext("SpecialCategory") == \
                                 "NIH Clinical Center trial":
                    # Only copy it if we still need it, else drop it
                    if needMagnusonInfo:
                        position = insertElement(newAdminElem, elem, position)
                        # Don't do this again later
                        needMagnusonInfo = False
                else:
                    position = insertElement(newAdminElem, elem, position)

        # If we have an active Magnuson Center site, add it now
        if needMagnusonInfo:
            elem = createMagnusonElem()
            position = insertElement(newAdminElem, elem, position)

        # Delete the old PDQAdminInfo
        if oldAdminElem is not None:
            ctgovTree.remove(oldAdminElem)

        # Locate the place where it goes and insert the new one
        position = 0
        found    = False
        for elem in ctgovTree.getchildren():
            # Position to point after this element
            position += 1

            # Insert will be after PDQIndexing element block
            if elem.tag == "PDQIndexing":
                found = True

                # Force the start of a new line, for whatever that's worth
                elem.tail = "\n"

                # Insert the new PDQAdminInfo
                ctgovTree.insert(position, newAdminElem)
                break
        if not found:
            fatal("Error, no PDQIndexing found in doc %s" % ctgovId)

        # Return the serial result
        newXml = etree.tostring(ctgovTree)
        return newXml


if __name__ == '__main__':
    # DEBUG
    cdr.logwrite("Request4690.py: starting")

    # Args
    if len(sys.argv) < 4:
        # DEBUG
        cdr.logwrite("Request4690.py: wrong arguments (%s)" % str(sys.argv))
        print("usage: Request4690.py uid pw {test|run}")
        sys.exit(1)
    uid   = sys.argv[1]
    pw    = sys.argv[2]

    testMode = None
    if sys.argv[3] == 'test':
        testMode = True
    elif sys.argv[3] == 'run':
        testMode = False
    else:
        fatal('Must specify "test" or "run"')
        sys.exit(1)

    # DEBUG
    # testMode = True

    # Instantiate our object
    filtTrans = FilterTransform()

    # Instantiate ModifyDocs job
    job = ModifyDocs.Job(uid, pw, filtTrans, filtTrans,
      "Global change to add data from former InScopeProtocol to current" +
      "CTGovProtocol.  Request 4690.", validate=True, testMode=testMode)

    # DEBUG
    # job.setMaxDocs(12)

    # Global change
    job.run()

    # DEBUG
    cdr.logwrite("Request4690.py: completed")
