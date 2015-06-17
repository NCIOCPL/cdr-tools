# ================================================================
# Request to update summary titles
# Every HP summary title needs to have a string of " for health
# professionals" (in English/Spanish) added
#                                               Volker Englisch
#                                               February 2015
#
# OCEPROJECT-2144: CDR - Loading NavLabel Spreadsheet
#
# $Id$
#
# ================================================================
import sys, lxml.etree as lxml, ModifyDocs, cdr, cdrdb, ExcelReader

class UpdateSummaryTitle:
    # ------------------------------------------------------
    #
    # ------------------------------------------------------
    def __init__(self, uid, pwd):
        # Save the passed name of the CDR ID file.
        # self.idFile = idFileName
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
        # and have the audience type of HP
        # ----------------------------------------------------
          #SELECT top 10 d.id AS "CDR-ID", q.value, l.value
        qry = """
          SELECT d.id AS "CDR-ID", q.value, l.value
            FROM document d
            JOIN doc_type dt
              ON d.doc_type = dt.id
             AND dt.name = 'Summary'
            JOIN pub_proc_cg cg
              ON d.id = cg.id
            JOIN query_term_pub q
              ON q.doc_id = d.id
             AND q.path = '/Summary/SummaryMetaData/SummaryAudience'
            JOIN query_term_pub l
              ON l.doc_id = d.id
             AND l.path = '/Summary/SummaryMetaData/SummaryLanguage'
           WHERE q.value = 'Health professionals'
           ORDER BY d.id
        """
        try:
            conn = cdrdb.connect()
            cursor = conn.cursor()
            cursor.execute(qry)
            rows = cursor.fetchall()
            self.job.log("Number of HP documents: %s" % len(rows))
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
            self.docIds = [62902, 256708]
            self.docIds = [62760, 62742, 62793, 62902]

        return self.docIds


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

        # If this is not a Summary the SELECT was way wrong
        # --------------------------------------------------
        if tree.tag != 'Summary':
            self.job.log("Doc %s is not a Summary doc.  Check SELECT" %
                          docObject.id)
            return docObject.xml

        # Find the AltTitle with TitleType="Navlabel", if it exists
        # ---------------------------------------------------------
        elem = tree.find(".//SummaryTitle")
        lang = tree.find(".//SummaryLanguage")

        # Checking if the Title element contains insertion/deletion markup
        # ----------------------------------------------------------------
        elemInsertion = elem.find("Insertion")
        elemDeletion  = elem.find("Deletion")

        if elemInsertion is not None or elemDeletion is not None:
            self.job.log("SummaryTitle contains Insertion/deletion markup." +
                         " Skipping document!!!")
            return docObject.xml

        #if not elem.text: # title contains markup instead '' or u''
        #    self.job.log("SummaryTitle contains markup. Skipping document!!!")
        #    return docObject.xml

        # Adding the required text string (including n-dash) to title
        # -----------------------------------------------------------
        tailEN = u' ' + unichr(8211) + ' for health professionals'
        tailES = u' ' + unichr(8211) + ' para profesionales de salud'

        if lang.text == 'English':
            # Don't add the title if it has already been added
            if elem.text.find('for health professionals') < 0:
                elem.text = elem.text + tailEN
            else:
                self.job.log("Summary title already changed in previous run!!!")
        else:
            # Don't add the title if it has already been added
            if elem.text.find('para profesionales') < 0:
                elem.text = elem.text + tailES
            else:
                self.job.log("Summary title already changed in previous run!!!")

        #print '============='

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
    "usage: NVCG_HPTitle.py userId pw live|test\n")
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
    obj = UpdateSummaryTitle(uid, pwd)
    job = ModifyDocs.Job(obj.session, None, obj, obj,
          "Update SummaryTitle for summary document (OCEPROJECT-2144)",
          validate=True, testMode=testMode)

    # So AddNavlabelTitle obj can log
    # ------------------------------------
    obj.job = job

    # Debug
    # -----
    if obj.debug or testMode:
        job.setMaxDocs(20)

    job.run()
