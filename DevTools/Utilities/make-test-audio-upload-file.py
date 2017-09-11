#----------------------------------------------------------------------
# Create a zipfile for testing CGI script ocecdr-3373.py.
#----------------------------------------------------------------------
import argparse
import glob
import random
import re
import zipfile
import lxml.etree as etree
import xlwt
import cdr
import cdrdb

class GlossaryTermName:
    """
    CDR document from which audio file will be linked.

    Class values:
        TEST_MP3 - filename of test audio file
        NS - namespace used in CDR XML documents
        NSMAP - namespace map used when creating CDR XML documents
        COLS - column headers for audio file manifest spreadsheet
        DEFINITION - dummy definition text for linked concept document
        COMMENT - note describing why these CDR documents were created
        SAVE_OPTS - arguments passed to cdr.addDoc()
        STATUS - string assigned to the status elements of the new documents
        logger - used to record information about this tool's activity

    Instance values:
        name - unique term name, randomly generated
        pron - pronunciation string
        cdr_id - string for CDR document ID in canonical 13-character format
        doc_id - integer version of the CDR document ID
    """

    TEST_MP3 = "test-audio-file.mp3"
    NS = "cips.nci.nih.gov/cdr"
    NSMAP = { "cdr": NS }
    COLS = (
        "CDR ID",
        "Term Name",
        "Language",
        "Pronunciation",
        "Filename",
        "Notes (Vanessa)",
        "Approved?",
        "Notes (NCI)"
    )
    DEFINITION = (
        "Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed "
        "do eiusmod tempor incididunt ut labore et dolore magna aliqua. "
        "Ut enim ad minim veniam, quis nostrud exercitation ullamco "
        "laboris nisi ut aliquip ex ea commodo consequat. "
        "Duis aute irure dolor in reprehenderit in voluptate velit "
        "esse cillum dolore eu fugiat nulla pariatur. "
        "Excepteur sint occaecat cupidatat non proident, sunt in "
        "culpa qui officia deserunt mollit anim id est laborum."
    )
    COMMENT = "creating document for testing audio upload"
    SAVE_OPTS = {
        "comment": COMMENT,
        "reason": COMMENT,
        "ver": "Y",
        "verPublishable": "N",
        "showWarnings": True
    }
    STATUS = "New pending"
    logger = cdr.Logging.get_logger("make-audio-upload-test")

    def __init__(self, credentials):
        """
        Create and save test CDR GlossaryTermName document.

        Also saves GlossaryTermConcept document to which this document links.

        Pass:
            credentials - session ID string or username, password tuple
        """

        rand_int = random.randint(100000000, 999999999)
        self.name = "test glossary term %d" % rand_int
        self.pron = "tehst GLAH-sah-ree turm"
        self.cdr_id = self.create_doc(credentials)
        self.doc_id = cdr.exNormalize(self.cdr_id)[1]

    def create_doc(self, credentials):
        """
        Create and store CDR CDR GlossaryTermName document.

        Also saves GlossaryTermConcept document to which this document links.

        Pass:
            credentials - session ID string or username, password tuple

        Return:
            CDR ID for new term name document in canonical string format
        """

        self.concept_id = self.create_concept_doc(credentials)
        print "concept ID", self.concept_id
        root = etree.Element("GlossaryTermName", nsmap=self.NSMAP)
        term_name = etree.SubElement(root, "TermName")
        etree.SubElement(term_name, "TermNameString").text = self.name
        etree.SubElement(term_name, "TermPronunciation").text = self.pron
        etree.SubElement(root, "TermNameStatus").text = self.STATUS
        spanish_name = etree.SubElement(root, "TranslatedName")
        etree.SubElement(spanish_name, "TermNameString").text = self.name
        status = etree.SubElement(spanish_name, "TranslatedNameStatus")
        status.text = self.STATUS
        concept = etree.SubElement(root, "GlossaryTermConcept")
        concept.set("{%s}ref" % self.NS, self.concept_id)
        xml = etree.tostring(root, pretty_print=True)
        doc = str(cdr.Doc(xml, "GlossaryTermName"))
        cdr_id, errors = cdr.addDoc(credentials, doc=doc, **self.SAVE_OPTS)
        if not cdr_id:
            raise Exception(errors)
        cdr.unlock(credentials, cdr_id)
        print "name ID", cdr_id
        return cdr_id

    def create_concept_doc(self, credentials):
        """
        Create the concept document to which the term name document links.

        Pass:
            credentials - identification of account used to create CDR doc

        Return:
            CDR ID for new concept document
        """

        root = etree.Element("GlossaryTermConcept", nsmap=self.NSMAP)
        gd = etree.SubElement(root, "GlossaryDefinition")
        etree.SubElement(gd, "DefinitionText").text = self.DEFINITION
        etree.SubElement(gd, "GlossaryAudience").text = "Health professional"
        etree.SubElement(root, "TermType").text = "Other"
        xml = etree.tostring(root, pretty_print=True)
        doc = str(cdr.Doc(xml, "GlossaryTermConcept"))
        concept_id, errors = cdr.addDoc(credentials, doc=doc, **self.SAVE_OPTS)
        if concept_id:
            cdr.unlock(credentials, concept_id)
            return concept_id
        raise Exception(errors)

    def add(self, zfile, week, sheet, row):
        """
        Populate the spreadsheet and the zipfile with data for this document.

        Pass:
            zfile - zip archive to which copies of the test audio file are
                    added
            week - string used for audio file copies' path name
            sheet - Excel worksheet to which rows are added
            row - starting position for rows added

        Return:
            integer for next row position on the worksheet
        """

        path = "%s/%d_en.mp3" % (week, self.doc_id)
        zfile.write(self.TEST_MP3, path)
        sheet.write(row, 0, self.doc_id)
        sheet.write(row, 1, self.name)
        sheet.write(row, 2, "English")
        sheet.write(row, 3, self.pron)
        sheet.write(row, 4, path)
        row += 1
        path = "%s/%d_es.mp3" % (week, self.doc_id)
        zfile.write(self.TEST_MP3, path)
        sheet.write(row, 0, self.doc_id)
        sheet.write(row, 1, self.name)
        sheet.write(row, 2, "Spanish")
        sheet.write(row, 4, path)
        return row + 1

    @classmethod
    def run(cls):
        """
        Collect command-line options and generate a new test file.

        Processing steps:
            1. parse and validate the command-line arguments
            2. create the test CDR documents
            3. create the zipfile for testing ocecdr-3373.py
            4. create the Excel workbook and worksheet for the manifest
            5. populate the zipfile and worksheet
            6. add the worksheet to the zipfile
            7. save the zipfile
        """

        random.seed()
        parser = argparse.ArgumentParser()
        group = parser.add_mutually_exclusive_group(required=True)
        parser.add_argument("--num-docs", type=int, default=1)
        group.add_argument("--user")
        group.add_argument("--session")
        args = parser.parse_args()
        credentials = args.session or (args.user, "")
        docs = [cls(credentials) for i in range(args.num_docs)]
        week = "Week_%03d" % cls.get_next_week()
        print "next week is %s" % week
        zpath = "d:/cdr/Audio_from_CIPSFTP/%s.zip" % week
        zfile = zipfile.ZipFile(zpath, "w")
        book = xlwt.Workbook(encoding="UTF-8")
        sheet = book.add_sheet("A")
        for i, label in enumerate(cls.COLS):
            sheet.write(0, i, label)
        row = 1
        for doc in docs:
            row = doc.add(zfile, week, sheet, row)
        name = "%s.xls" % week
        path = "d:/tmp/%s" % name
        book.save(path)
        zfile.write(path, "%s/%s" % (week, name))
        zfile.close()
        print "saved", zpath

    @classmethod
    def get_next_week(cls):
        cursor = cdrdb.connect().cursor()
        last_week = 0
        paths = glob.glob("d:/cdr/Audio_from_CIPSFTP/Week_*.zip")
        names = set([p.replace("\\", "/").split("/")[-1] for p in paths])
        query = cdrdb.Query("term_audio_zipfile", "filename")
        names |= set([row[0] for row in query.execute(cursor).fetchall()])
        for name in names:
            match = re.match(r"Week_(\d{3})[._].*zip", name)
            if match:
                week = int(match.group(1))
                if week > last_week:
                    last_week = week
        return last_week + 1

GlossaryTermName.run()
