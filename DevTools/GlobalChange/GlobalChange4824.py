#----------------------------------------------------------------------
#
# $Id$
#
# Add CTGovDuplicate elements to InScopeProtocol documents.
#
# BZIssue::4824
#
#----------------------------------------------------------------------
import cdr, ExcelReader, ModifyDocs, sys, lxml.etree as etree

LOGFILE = 'd:/cdr/log/GlobalChange4824.log'

#----------------------------------------------------------------------
# This class has two methods, one to return a list of CDR document
# ID for the documents to be transformed, and the other to take a
# document object and return a (possibly) modified copy of that
# object's xml member.
#----------------------------------------------------------------------
class GlobalChange4824:
    def __init__(self, workbookName):
        book = ExcelReader.Workbook(workbookName)
        sheet = book[0]
        self.docIds = []
        for row in sheet:
            try:
                self.docIds.append(int(row[0].val))
            except:
                pass
    def getDocIds(self):
        return self.docIds
    def run(self, docObj):
        tree = etree.XML(docObj.xml)
        position = 0
        for node in tree:
            if node.tag == 'CTGovDuplicate':
                break
            elif node.tag == 'ProtocolIDs':
                tree.insert(position, etree.Element('CTGovDuplicate'))
                break
            else:
                position += 1
        return etree.tostring(tree, encoding='utf-8', xml_declaration=True)
        
#----------------------------------------------------------------------
# Collect the data to be added to the protocol docs.
#----------------------------------------------------------------------
if len(sys.argv) < 5 or sys.argv[4] not in ('test', 'live'):
    sys.stderr.write("usage: Request4824.py uid pwd input-doc test|live\n")
    sys.exit(1)
obj = GlobalChange4824(sys.argv[3])
testMode = sys.argv[4] == 'test'
cdr.logwrite("running in %s mode" % sys.argv[4], LOGFILE)
job = ModifyDocs.Job(sys.argv[1], sys.argv[2], obj, obj,
                     "Adding CTGovDuplicate elements (request #4824).",
                     testMode=testMode, logFile=LOGFILE)
job.run()
