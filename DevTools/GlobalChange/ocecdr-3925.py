#----------------------------------------------------------------------
#
# $Id:$
#
# Global change to strip the Compact attribute from lists.
#
# JIRA::OCECDR-3925
#
#----------------------------------------------------------------------
import cdr
import cdrdb
import lxml.etree as etree
import ModifyDocs
import sys
import time

LOGFILE = cdr.DEFAULT_LOGDIR + "/ocecdr-3925.log"

class Control:
    def __init__(self):
        self.start = time.time()
        cursor = cdrdb.connect("CdrGuest").cursor()
        cursor.execute("""\
SELECT id
  FROM document
 WHERE xml LIKE '%list%compact%'""")
        self.ids = [row[0] for row in cursor.fetchall()]
    def getDocIds(self):
        return sorted(self.ids)
    def run(self, docObj):
        tree = etree.XML(docObj.xml)
        etree.strip_attributes(tree, 'Compact')
        return etree.tostring(tree, encoding="utf-8", xml_declaration=True)

#----------------------------------------------------------------------
# Create the job object and run the job.
#----------------------------------------------------------------------
if len(sys.argv) < 4 or sys.argv[3] not in ('test', 'live'):
    sys.stderr.write("usage: ocecdr-3925.py uid pwd test|live\n")
    sys.exit(1)
obj = Control()
testMode = sys.argv[3] == 'test'
cdr.logwrite("running in %s mode" % sys.argv[3], LOGFILE)
job = ModifyDocs.Job(sys.argv[1], sys.argv[2], obj, obj,
                     "Strip Compact attribute from lists (OCECDR-3925)",
                     testMode=testMode, logFile=LOGFILE)
job.run()
cdr.logwrite("elapsed: %s seconds" % (obj.start - time.time()))
