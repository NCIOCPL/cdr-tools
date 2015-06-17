# ================================================================
# Request to add a new, optional AltTitle element with type 
# "Navlabel" for Summaries. 
# The text for the Navlabel comes from a spreadsheet.
#                                               Volker Englisch
#                                               February 2015
#
# OCEPROJECT-2144: CDR - Loading NavLabel Spreadsheet
#
# $Id$
#
# ================================================================
import sys, lxml.etree as lxml, ModifyDocs, cdr, cdrdb, ExcelReader

class AddNavlabelTitle:
    # ------------------------------------------------------
    #
    # ------------------------------------------------------
    def __init__(self, uid, pwd, navlabels):
        # Save the passed name of the CDR ID file.
        self.navlabels = navlabels
        self.job    = None
        self.debug  = False #True  #False
        self.update = True  # in case we only want to add new ones
        self.session = cdr.login(uid, pwd)
        error = cdr.checkErr(self.session)
        if error:
            raise Exception("Failure logging into CDR: %s" % error)

    # ------------------------------------------------------
    # GetDocIds method that's called by ModifyDocs to identify
    # all documents to be changed.  The result has to be a list.
    # How to create the list is not important: SQL select from 
    # database, read IDs from file, 
    #
    # Getting the CDR-ids from a spreadsheet because only 
    # about half of the document will actually need to be 
    # updated.  For all others navlabel = ''.
    # ------------------------------------------------------
    def getDocIds(self):
        self.docIds = []
        for docId in self.navlabels.keys():
            if self.navlabels[docId]:
               #print "%s - %s" % (docId, self.navlabels[docId])
               self.docIds.append(docId)

        self.docIds.sort()

        # We're reading the CDR-IDs from a spreadsheet.  This spreadsheet
        # has probably been created on the production machine.  If we're
        # running the job on a lower tier not all of the new documents
        # will exist depending on how old the data is.
        # Let's double-check if the ID exists on this server.
        # This portion is not needed on PROD.
        # ---------------------------------------------------------------
        # All Summaries that have been published to Cancer.gov
          #SELECT top 10 d.id AS "CDR-ID"
        qry = """
          SELECT d.id AS "CDR-ID"
            FROM document d
            JOIN doc_type dt
              ON d.doc_type = dt.id
            JOIN pub_proc_cg cg
              ON d.id = cg.id
      LEFT OUTER JOIN query_term m
              ON m.doc_id = d.id
             AND m.path = '/Summary/@ModuleOnly'
           WHERE dt.name = 'Summary'
             AND m.value is null
           ORDER BY d.id
        """
        try:
            conn = cdrdb.connect()
            cursor = conn.cursor()
            cursor.execute(qry)
            rows = cursor.fetchall()
            self.job.log("Number of Summary documents: %s" % len(rows))
            cursor.close()
        except cdrdb.Error as info:
            self.job.log("Database error selecting ids: %s" % str(info))
            sys.exit(1)

        # list of IDs on the spreadsheet but not in the database
        # ------------------------------------------------------
        dbIds = [row[0] for row in rows]
        tempIds = list(set(self.docIds) - set(dbIds))
        leftIds = list(set(self.docIds) - set(tempIds))
        self.docIds = leftIds

        return self.docIds

#    # ------------------------------------------------------
#    # GetDocIds method that's called by ModifyDocs to identify
#    # all documents to be changed.  The result has to be a list.
#    # How to create the list is not important: SQL select from 
#    # database, read IDs from file, 
#    # ------------------------------------------------------
#    def getDocIds(self):
#        # All Summaries that have been published to Cancer.gov
#          #SELECT top 10 d.id AS "CDR-ID"
#        qry = """
#          SELECT d.id AS "CDR-ID"
#            FROM document d
#            JOIN doc_type dt
#              ON d.doc_type = dt.id
#            JOIN pub_proc_cg cg
#              ON d.id = cg.id
#           WHERE dt.name = 'Summary'
#           ORDER BY d.id
#        """
#        try:
#            conn = cdrdb.connect()
#            cursor = conn.cursor()
#            cursor.execute(qry)
#            rows = cursor.fetchall()
#            self.job.log("Number of Summary documents: %s" % len(rows))
#            cursor.close()
#        except cdrdb.Error as info:
#            self.job.log("Database error selecting ids: %s" % str(info))
#            sys.exit(1)
#
#        # Creating the list of doc IDs
#        self.docIds = [row[0] for row in rows]
#
#        # Debug
#        # -----
#        # English and Spanish summary for testing
#        if self.debug:  
#            #self.docIds = [62902, 256708]
#            self.docIds = [ 62972, 446580, 445441, 458088, 62891, 269124, 269044, 62907, 62864, 257989, 269587, 256643, 256638, 256661, 732778, 733565, 732631, 732670, 256664, 256641]
#
#        return self.docIds
#

    # ------------------------------------------------------
    # Run method that's called by ModifyDocs.py
    # ------------------------------------------------------
    def run(self, docObject):
        # Is the document valid before transformation?
        # --------------------------------------------
        result = cdr.valDoc(self.session, 'Summary',
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
        if tree.tag != 'Summary':
            self.job.log("Doc %s is not a Summary doc.  Check SELECT" %
                          docObject.id)
            return docObject.xml

        # Return if we don't need to add a navlabel or if the document 
        # doesn't exist anymore and is not on the spreadsheet 
        # -----------------------------------------
        navlabel = ''
        docId = cdr.exNormalize(docObject.id)[1]
        if docId in navlabels:
            navlabel = self.navlabels[docId]

        if not navlabel:
            self.job.log("Doc %s has no navlabel.  Skipping" %
                          docObject.id)
            return docObject.xml
            
        # Find the AltTitle with TitleType="Navlabel", if it exists
        # ---------------------------------------------------------
        navTitle = tree.find("AltTitle[@TitleType]")

        # Locate the ContactMode element.  It's required.  GovernmentEmployee
        # goes directly after it if no Affiliations exist. If Affiliations do
        # exist it goes after those.
        # -------------------------------------------------------------------
        sumTitle = tree.xpath("./SummaryTitle")
        navTitle = tree.xpath("./AltTitle[@TitleType='Navlabel']")

        # If we don't find exactly one SummaryTitle something is 
        # seriously wrong
        # -----------------------------------------------------
        if len(sumTitle) != 1:
            self.job.log("Doc %s has %d Title elements - skipping" %
                      (docObject.id, len(sumTitle)))
            return docObject.xml

        # Create the new element text and the element
        # -------------------------------------------
        # geElemText = "Read from Spreadsheet"
        geElemText = navlabel
        geElem = tree.makeelement("AltTitle", TitleType='Navlabel')
        geElem.text = geElemText

        # Add the Navlabel Title if it doesn't already exist
        # --------------------------------------------------
        # Add Navlabel if it doesn't exist and update existing one
        if self.update:
            if len(navTitle) > 0:
                # Navlabel title already exists
                navTitle[0].text = geElemText
            else:
                sumTitle[0].addnext(geElem)
        # Only add Navlabel if it doesn't already exist
        else:
            if len(navTitle) > 0:
                # Navlabel title already exists
                dada = 1
                #navTitle[0].addnext(geElem)
            else:
                sumTitle[0].addnext(geElem)

        # Return serialization of the modified document
        # ---------------------------------------------
        if self.debug:
            print '****** Updated Document ******'

        newDoc = lxml.tostring(tree)

        # Is the document valid after transformation?
        # -------------------------------------------
        result = cdr.valDoc(self.session, 'Summary', doc = newDoc)
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
    "usage: NVCGNavLabel.py userId pw live|test\n")
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

    # Reading the Navlabel text from the spreadsheet
    # ----------------------------------------------
    filename = 'NVCG_Urls.xls'
    book = ExcelReader.Workbook(filename)
    sheet = book[0]
    navlabels = {}
    iRow = 0
    iNoNavs = 0
    
    print "Reading Spreadsheet"
    print "==================="
    for row in sheet:
        try:
            iRow += 1
            # Skip over header rows
            try:
                int(row[0].val)
            except:
                if row[0]:
                    print "Row %3d: Skipping header: %s" % (iRow, row[0].val)
                else:
                    print "Row %3d: Skipping empty row" % iRow
                continue

            docId = int(row[0].val)

            # Not all records have a new Navlabel
            try:
                navlabel = row[10].val
            except:
                iNoNavs += 1
                print "Row %3d: No Nav found for %s - %s" % (iRow, 
                                                          int(row[0].val), 
                                                          row[7].val)
                navlabel = ''

            navlabels[docId] = navlabel
        except Exception, e:
            print e

    print "==================="
    print ""

    # Create the job object
    # ---------------------
    obj = AddNavlabelTitle(uid, pwd, navlabels)
    job = ModifyDocs.Job(obj.session, None, obj, obj,
          "Add AltTitle TitleType='Navlabel' to a summary document "
          "(OCEPROJECT-2144)",
          validate=True, testMode=testMode)

    # So AddNavlabelTitle obj can log
    # ------------------------------------
    obj.job = job

    # Debug
    # -----
    if obj.debug or testMode:
        job.setMaxDocs(10)

    job.run()
