#----------------------------------------------------------------------
#
# $Id$
#
# Add PurposeText to all Summaries in a specified list of Summaries.
#
# Two lists of Summaries have been prepared in Excel spreadsheets, one
# for English and one for Spanish language Summaries.
#
# Each row in the spreadsheet provides CDR ID, Summary title, Purpose text.
# The purpose text is a phrase to substitute into a placeholder in generic
# text describing the purpose of the summary.  It is not a complete
# sentence but will be integrated into a complete sentence by a publishing
# output filter.
#
# Each spreadsheet should be prepared for use by creating a tab separated
# Unicode encoded text file (In Excel, Choose "Save As / Save as type"
# "Unicode Text (*.txt)."
#
# Run the program twice, once for the English sheet, once for Spanish.
# Provide the name of the file on the command line.
#
# BZIssue::4863
#
#----------------------------------------------------------------------
import sys, codecs, cdr, ModifyDocs

# We've done lots of these in XSL/T, let's do a few with etree
# It might actually be a bit simpler
etree = cdr.importEtree()

class Transform:
    """
    Contains getDocIds() and run() methods for ModifyDocs.
    """
    def __init__(self, inFile):
        """
        Load the input file, a tab separated Unicode encoded file of
            CDR ID<tab>title(unused)<tab>purpose text
        Create a dictionary of:
            ID => PurposeText

        Pass:
            Name of tab delimited, 2 byte Unicode encoded, file.
        """
        # Will replace this with a reference to ModifyDocs job for logging
        self.job = None

        # Open the tab sep spreadsheet file and read in 16 bit unicode
        try:
            fp = codecs.open(inFile, "r", "utf-16")
        except Exception, info:
            sys.stderr.write("Unable to open input file: %s" % info)
            sys.exit(1)
        try:
            lineData = fp.read()
        except Exception, info:
            sys.stderr.write("Error reading unicode text: %s" % info)
            sys.exit(1)

        # Load a dictionary of cdrId => purpose text
        lines          = lineData.split("\n")
        self.idPurpose = {}
        lineCnt        = 0
        recsLoaded     = 0
        while lineCnt < len(lines):
            # Skip blank lines or lines with just column tabs and newlines
            if not lines[lineCnt] or len(lines[lineCnt]) < 5:
                lineCnt += 1
                continue

            # Parse the info from one line (English) or two (Spanish)
            try:
                cdrIdStr, title, text = lines[lineCnt].split(u"\t")
                cdrIdNum = self.getCdrIdNum(cdrIdStr)
                lineCnt += 1
                if cdrIdNum == 0:
                    # cdrIdStr, dummy1, dummy2 = lines[lineCnt].split(u"\t")
                    # cdrIdNum = self.getCdrIdNum(cdrIdStr)
                    # Nothing we need on this line
                    continue
            except Exception, info:
                sys.stderr.write("Format error on line: %d: '%s'" %
                      (lineCnt, lines[lineCnt].encode('ascii', 'replace')))
                sys.exit(1)

            # Remove newlines and quotes added by Excel
            # Quotes appear on any strings with commas, even though it's tab
            #   delimited data.
            text = text.rstrip()
            text = text.strip('"')

            # Some lines indicate docs with no PurposeText
            if text.lower() == "no section":
                continue

            # Save id and text
            self.idPurpose[cdrIdNum] = text
            recsLoaded += 1

        print("Loaded a total of %d records" % recsLoaded)


    def getDocIds(self):
        """
        Return a list of CDR IDs to be changed.
        """
        docIds = self.idPurpose.keys()
        docIds.sort()
        return docIds


    def getCdrIdNum(self, cdrIdStr):
        """
        Convert a CDR ID string to an integer or 0 if failed.

        Pass:
            Unicode or other string.

        Return:
            Integer, 0 if conversion failed.
        """
        try:
            cdrId = cdr.exNormalize(cdrIdStr)[1]
        except cdr.Exception:
            return 0
        return cdrId


    def run(self, docObj):
        """
        If no PurposeText already present, add one at the end of the
        SummaryMetaData.

        Pass:
            ModifyDocs Doc object for the document to transform.
        """
        cdrId  = cdr.exNormalize(docObj.id)[1]
        oldXml = docObj.xml

        # Skip docs with no associated text
        if not self.idPurpose.has_key(cdrId):
            return oldXml

        # Skip if the text is "no section"
        pText = self.idPurpose[cdrId]
        if pText.lower() == "no section":
            return oldXml

        # We've got what we want, parse doc
        tree = etree.fromstring(oldXml)

        # Does it already have PurposeText?
        if tree.findall("PurposeText"):
            self.job.log("CDR ID: %d already has PurposeText skipping." % cdrId)
            return oldXml

        # Create the new element as last subelement under metadata
        parent = tree.findall("SummaryMetaData")
        if not parent:
            sys.stderr.write("No SummaryMetaData in CDR ID = %d" % cdrId)
            sys.exit(1)
        elem = etree.SubElement(parent[0], "PurposeText")
        elem.text = pText
        elem.tail = "\n"

        # Return serial xml
        return etree.tostring(tree, encoding='utf-8')


#----------------------------------------------------------------------
#   Main
#----------------------------------------------------------------------
if __name__ == "__main__":

    # Args
    if len(sys.argv) < 5:
        print("usage: Request4863.py uid pw tabfile {test|run}")
        sys.exit(1)
    uid     = sys.argv[1]
    pw      = sys.argv[2]
    tabfile = sys.argv[3]

    # Test / run mode
    testMode = None
    print(sys.argv[4].lower())
    if sys.argv[4].lower() == 'test':
        testMode = True
    elif sys.argv[4].lower() == 'run':
        testMode = False
    else:
        sys.stderr.write('Must specify "test" or "run"')
        sys.exit(1)

    # Instantiate our object, loading the spreadsheet
    transform = Transform(tabfile)

    # Debug
    # testMode = 'test'

    # Instantiate ModifyDocs job
    job = ModifyDocs.Job(uid, pw, transform, transform,
      'Global change to add PurposeText elements to Summaries.  Request 4863.',
      validate=True, testMode=testMode)

    # Install access to job in FilterTransform for logging
    transform.job = job

    # Debug
    # job.setMaxDocs(20)

    # Global change
    job.run()
