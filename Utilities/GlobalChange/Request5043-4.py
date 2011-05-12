#----------------------------------------------------------------------
#
# $Id$
#
# Modify the boiler plate text in the
#   /DrugInformationSummary/DrugInfoMetaData/Description element
#
# Replaces the various non-standard texts with one of two standard
# descriptions, one for single agents and one for drug combinations.
#
# BZIssue::5043
# BZIssue::5044
#
#                                       Alan Meyer
#                                       May, 2011
#----------------------------------------------------------------------
import ModifyDocs, cdrdb, sys, re, lxml.etree as etree

SINGLE_DESC = "This page contains brief information about @@TITLE@@ and a collection of links to more information about the use of this drug, research results, and ongoing clinical trials."

COMBO_DESC = "This page contains brief information about the drug combination called @@TITLE@@. The drugs in the combination are listed, and links to individual drug summaries are included."

CAP_PAT = re.compile("[A-Z][A-Z]")
ONE_PAT = re.compile("^[A-Z]$")

class OneOffGlobal:
    def __init__(self):
        self.job = None

    def fatal(self, msg):
        sys.stderr.write(msg)
        self.job.log(msg)
        sys.exit(1)

    def getDocIds(self):
        qry = """
        SELECT d.id
          FROM document d, doc_type t
         WHERE d.doc_type = t.id
           AND t.name = 'DrugInformationSummary'
         ORDER BY d.id
        """
        try:
            conn = cdrdb.connect()
            cursor = conn.cursor()
            cursor.execute(qry)
            rows = cursor.fetchall()
            cursor.close()
        except cdrdb.Error as info:
            self.fatal("Database error selecting ids: %s" % str(info))

        self.docIds = [row[0] for row in rows]

        # DEBUG
        # self.docIds = [632567,]

        return self.docIds


    def run(self, docObject):

        docId = docObject.id
        xml   = docObject.xml

        # Parse the xml
        tree = etree.fromstring(xml)

        # Locate description
        descNodes = tree.findall('DrugInfoMetaData/Description')
        if len(descNodes) != 1:
            self.fatal("DocId %s has %d descriptions!" %
                       (docId, len(descNodes)))
        desc = descNodes[0]

        # Locate the name of the drug
        titleNodes = tree.findall('Title')
        if len(titleNodes) != 1:
            self.fatal("DocId %s has %d titles!" % (docId, len(titleNodes)))
        title = titleNodes[0].text

        # Change capitalization of the name - Experimental
        # If there are two capital letters in a row in a word, leave it
        #  alone.
        # Else lower case it
        titleWords = []
        words = title.split()
        for w in words:
            if CAP_PAT.search(w) or ONE_PAT.match(w):
                titleWords.append(w)
            else:
                titleWords.append(w.lower())
        normTitle = " ".join(titleWords)

        # Is this a combination drug?
        descText = SINGLE_DESC
        comboNodes = tree.xpath(
         '/DrugInformationSummary/DrugInfoMetaData/DrugInfoType/@Combination')
        if len(comboNodes) == 1:
            if comboNodes[0] == "Yes":
                descText = COMBO_DESC

        # Replace the place holder with the name of the drug(s)
        descText = descText.replace("@@TITLE@@", normTitle)

        # Replace the existing description in the document with the new one
        desc.text = descText

        # Return re-serialization
        return etree.tostring(tree)


if __name__ == "__main__":
    if len(sys.argv) != 4 or sys.argv[3] not in ('test', 'live'):
        sys.stderr.write("usage: %s uid pwd test|live\n" % sys.argv[0])
        sys.exit(1)
    uid, pwd, flag = sys.argv[1:]
    testMode = flag == 'test'
    obj = OneOffGlobal()
    job = ModifyDocs.Job(uid, pwd, obj, obj,
             'Modify the Description element for Bugzilla request 5044',
             validate=True, testMode=testMode)
    obj.job = job

    # Debug
    # job.setMaxDocs(10)
    job.run()
