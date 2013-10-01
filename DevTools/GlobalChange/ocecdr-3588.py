#----------------------------------------------------------------------
#
# $Id$
#
# Populate new Public attribute for Term/NCIThesaurusConcept element.
#
# BZIssue::5287 / JIRA::OCECDR-3588
#
#----------------------------------------------------------------------
import ModifyDocs, lxml.etree as etree, cdrdb, sys

COMMENT = "Set Public attribute for thesaurus codes (OCECDR-3588)"

class Transform:
    def __init__(self, liveCodes):
        self.docIds = set()
        self.liveCodes = liveCodes
        cursor = cdrdb.connect("CdrGuest").cursor()
        cursor.execute("""\
SELECT doc_id, value
  FROM query_term
 WHERE path = '/Term/NCIThesaurusConcept'""")
        for docId, code in cursor.fetchall():
            if code.strip() in liveCodes:
                self.docIds.add(docId)
                # Debugging
                # if len(self.docIds) >= 10:
                #     break
    def getDocIds(self):
        return sorted(self.docIds)
    def run(self, docObj):
        tree = etree.XML(docObj.xml)
        for node in tree.findall("NCIThesaurusConcept"):
            code = node.text.strip()
            if code in self.liveCodes:
                node.set("Public", "Yes")
        return etree.tostring(tree, encoding="utf-8")

def loadCodes(codeFile):
    codes = set()
    for line in open(codeFile):
        if line.startswith("LIVE "):
            codes.add(line[5:].strip())
    return codes

def main():
    if len(sys.argv) < 5 or sys.argv[4] not in ("test", "run"):
        sys.stderr.write("usage: ocecdr-3588.py uid pwd code-file {test|run}\n")
        sys.exit(1)
    uid, pwd, codeFile = sys.argv[1:4]
    testMode = sys.argv[4] == "test"
    liveCodes = loadCodes(codeFile)
    transform = Transform(liveCodes)
    job = ModifyDocs.Job(uid, pwd, transform, transform, COMMENT,
                         validate=True, testMode=testMode)
    job.run()

if __name__ == "__main__":
    main()
