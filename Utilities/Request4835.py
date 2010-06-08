#----------------------------------------------------------------------
#
# $Id$
#
# Populate affiliation information extracted from cancer.gov HTML pages.
#
# BZIssue::4835
#
#----------------------------------------------------------------------
import cdr, cdrdb, re, sys, ModifyDocs, lxml.etree as etree, cgi

LOGFILE = 'd:/cdr/log/Request4835.log'

#----------------------------------------------------------------------
# This class has two methods, one to return a list of CDR document
# ID for the documents to be transformed, and the other to take a
# document object and return a (possibly) modified copy of that
# object's xml member.
#----------------------------------------------------------------------
class FilterAndTransform:
    def __init__(self, tree):
        self.affiliations = {}
        for member in tree.findall('PDQBoardMember'):
            docId = int(member.get('board-member-id'))
            affiliations = member.findall('Affiliations')
            self.affiliations[docId] = affiliations[0]
    def getDocIds(self):
        return self.affiliations.keys()
    def run(self, docObj):
        docId = cdr.exNormalize(docObj.id)[1]
        tree = etree.XML(docObj.xml)
        for sibling in tree.findall('BoardMemberContactMode'):
            sibling.addnext(self.affiliations[docId])
        return etree.tostring(tree, encoding='utf-8', xml_declaration=True)

#----------------------------------------------------------------------
# Collect the data to be added to the protocol docs.
#----------------------------------------------------------------------
if len(sys.argv) < 5 or sys.argv[4] not in ('test', 'live'):
    sys.stderr.write("usage: Request4835.py uid pwd input-doc test|live\n")
    sys.exit(1)
fileName = sys.argv[3]
xmlDoc   = open(fileName, 'rb').read()
tree     = etree.XML(xmlDoc)
obj      = FilterAndTransform(tree)
testMode = sys.argv[4] == 'test'
cdr.logwrite("running in %s mode" % sys.argv[4], LOGFILE)
job = ModifyDocs.Job(sys.argv[1], sys.argv[2], obj, obj,
                     "Adding Affiliations (request #4835).",
                     testMode = testMode, logFile = LOGFILE)
sys.stdout.flush()
job.run()
