# ================================================================
# Request to update DIS Urls
#                                               Volker Englisch
#                                               March 2015
#
# OCEPROJECT-2601: Publish PDQ Drug Info Summaries to 
#                  "/cancertopics/treatment/drugs" for UAT
#
# $Id$
#
# ================================================================
import sys, lxml.etree as lxml, ModifyDocs, cdr, cdrdb

class UpdateSummaryUrl:
    # ------------------------------------------------------
    #
    # ------------------------------------------------------
    def __init__(self, uid, pwd):
        # Save the passed file name of the URLs.
        self.job    = None
        self.debug  = False #True  #False
        self.update = True
        self.session = cdr.login(uid, pwd)
        error = cdr.checkErr(self.session)
        if error:
            raise Exception("Failure logging into CDR: %s" % error)

    # ------------------------------------------------------
    # GetDocIds method that's called by ModifyDocs to identify
    # all documents to be changed.  The result has to be a list.
    # How to create the list is not important: SQL select from 
    # database, read IDs from file, etc.
    # ------------------------------------------------------
    def getDocIds(self):
        # All Summaries that have been published to Cancer.gov
          #SELECT top 5 d.id AS "CDR-ID"
        qry = """
          SELECT d.id AS "CDR-ID"
            FROM document d
            JOIN doc_type dt
              ON d.doc_type = dt.id
            JOIN pub_proc_cg cg
              ON d.id = cg.id
           WHERE dt.name = 'DrugInformationSummary'
           ORDER BY d.id
        """
        try:
            conn = cdrdb.connect()
            cursor = conn.cursor()
            cursor.execute(qry)
            rows = cursor.fetchall()
            self.job.log("Number of DIS documents: %s" % len(rows))
            cursor.close()
        except cdrdb.Error as info:
            self.job.log("Database error selecting ids: %s" % str(info))
            sys.exit(1)

        # Creating the list of doc IDs
        self.docIds = [row[0] for row in rows]

        # Debug
        # -----
        # English and Spanish summary for testing
        if self.debug:  
            self.docIds = [526103, 688288, 495426]

        return self.docIds


    # ------------------------------------------------------
    # Run method that's called by ModifyDocs.py
    # ------------------------------------------------------
    def run(self, docObject):
        # Is the document valid before transformation?
        # --------------------------------------------
        result = cdr.valDoc(self.session, 'DrugInformationSummary',
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

        # If this is not a Summary the SELECT was wrong
        # ---------------------------------------------
        if tree.tag != 'DrugInformationSummary':
            self.job.log("Doc %s is not a DIS doc.  Check SELECT" %
                          docObject.id)
            return docObject.xml

        # Find the SummaryUrl
        # -------------------
        elem = tree.find(".//URL")

        # Create the new element text and the element
        # -------------------------------------------
        docId = cdr.exNormalize(docObject.id)[1]

        # If the CDR-ID is missing on the spreadsheet, skip it
        # ----------------------------------------------------
        try:
            url = elem.attrib['{cips.nci.nih.gov/cdr}xref']
            newUrl = url.replace('cancertopics/druginfo', 'about-cancer/treatment/drugs')
            elem.attrib['{cips.nci.nih.gov/cdr}xref'] = newUrl
        except:
            self.job.log("Doc %s not updated.  Check url." %
                          docObject.id)
            return docObject.xml

        # Return serialization of the modified document
        # ---------------------------------------------
        if self.debug:
            print '****** Updated Document ******'

        newDoc = lxml.tostring(tree)

        # Is the document valid after transformation?
        # -------------------------------------------
        result = cdr.valDoc(self.session, 'DrugInformationSummary', 
                            doc = newDoc)
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
    "usage: NVCG_DISUrl.py userId pw live|test\n")
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

#    # Reading the Url text from the spreadsheet
#    # ----------------------------------------------
#    filename = 'NVCG_Urls.xls'
#    book = ExcelReader.Workbook(filename)
#    sheet = book[0]
#    urls = {}
#    iRow = 0
#    iNoUrl = 0
#    
#    print "Reading Spreadsheet"
#    print "==================="
#    for row in sheet:
#        try:
#            iRow += 1
#            # Skip over header rows
#            try:
#                int(row[0].val)
#            except:
#                if row[0]:
#                    print "Row %3d: Skipping header: %s" % (iRow, row[0].val)
#                else:
#                    print "Row %3d: Skipping empty row" % iRow
#
#                continue
#
#            docId = int(row[0].val)
#
#            # Not all records have a new Url
#            try:
#                url = row[12].val
#            except:
#                iNoUrl += 1
#                print "Row %3d: No URL found for %s - %s" % (iRow, 
#                                                          int(row[0].val), 
#                                                          row[7].val)
#                continue
#
#            #navlabels[docId] = navlabel
#            urls[docId] = "http://www.cancer.gov%s" % url
#        except Exception, e:
#            print e
#
#    print "==================="
#    print ""

    # Create the job object
    # ---------------------
    obj = UpdateSummaryUrl(uid, pwd)
    job = ModifyDocs.Job(obj.session, None, obj, obj,
          "Update SummaryUrl for summary document (OCEPROJECT-2144)",
          validate=True, testMode=testMode)

    # So UpdateSummaryUrl obj can log
    # ------------------------------------
    obj.job = job

    # Debug
    # -----
    if obj.debug or testMode:
        job.setMaxDocs(20)

    job.run()
