#----------------------------------------------------------------------
#
# $Id$
#
# Add CTGovDuplicate elements to InScopeProtocol documents.
#
# BZIssue::4824
#
#----------------------------------------------------------------------
import ExcelReader, cdrdb, ModifyDocs, sys, lxml.etree as etree

LOGFILE = 'd:/cdr/log/GlobalChange4824.log'

#----------------------------------------------------------------------
# This class has two methods, one to return a list of CDR document
# ID for the documents to be transformed, and the other to take a
# document object and return a (possibly) modified copy of that
# object's xml member.
#----------------------------------------------------------------------
class GlobalChange4824:
    class Trial:
        def __init__(self, row, cursor):
            self.cdrId = int(row[0].val]
            self.nctId = row[1].val
            cursor.execute("""\
                SELECT ...""")
    def __init__(self, workbookName, cursor):
        book = ExcelReader(workbookName)
        sheet = book[0]
        self.trials = {}
        for row in sheet:
            try:
                trial = GlobalChange4824.Trial(row, cursor)
                self.trials[trial.cdrId] = trial
            except:
                pass
    def getDocIds(self):
        return self.trials.keys()
    def run(self, docObj):
        
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
                     "Adding CTGovDuplicate elements (request #4824).",
                     testMode = testMode, logFile = LOGFILE)
job.run()
