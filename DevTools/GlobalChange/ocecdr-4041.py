#----------------------------------------------------------------------
#
# $Id$
#
# Global change to change the CAM summary type.
#
# JIRA::OCECDR-4041
#
#----------------------------------------------------------------------
import cdr
import cdrdb
import lxml.etree as etree
import ModifyDocs
import sys
import time

LOGFILE = cdr.DEFAULT_LOGDIR + "/ocecdr-4041.log"

class Control:
    def __init__(self):
        self.start = time.time()
        cursor = cdrdb.connect("CdrGuest").cursor()
        cursor.execute("""\
SELECT doc_id
  FROM query_term
 WHERE path = '/Summary/SummaryMetaData/SummaryType'
   AND value = 'Complementary and alternative medicine'""")
        self.ids = [row[0] for row in cursor.fetchall()]
    def getDocIds(self):
        return sorted(self.ids)
    def run(self, docObj):
        root = etree.XML(docObj.xml)
        for node in root.findall("SummaryMetaData/SummaryType"):
            if node.text.lower() == "complementary and alternative medicine":
                node.text = ("Integrative, alternative, and complementary "
                             "therapies")
        return etree.tostring(root, encoding="utf-8", xml_declaration=True)

#----------------------------------------------------------------------
# Create the job object and run the job.
#----------------------------------------------------------------------
if len(sys.argv) < 3 or sys.argv[2] not in ('test', 'live'):
    sys.stderr.write("usage: ocecdr-4041.py session test|live\n")
    sys.exit(1)
obj = Control()
testMode = sys.argv[2] == 'test'
cdr.logwrite("running in %s mode" % sys.argv[2], LOGFILE)
job = ModifyDocs.Job(sys.argv[1], "", obj, obj,
                     "Change CAM summary type name (OCECDR-4041)",
                     testMode=testMode, logFile=LOGFILE)
job.run()
cdr.logwrite("elapsed: %s seconds" % (obj.start - time.time()))
