#----------------------------------------------------------------------
#
# $Id$
#
# Global change to change CAM miscellaneous document types.
#
# JIRA::OCECDR-4047
#
# Modified 2016-04-11 because the users changed their minds about
# some of the new values. This version, in addition to changing
# the old values to the new ones, also fixes the values that were
# changed on the lower tiers to the wrong new values.
#
#----------------------------------------------------------------------
import cdr
import cdrdb
import lxml.etree as etree
import ModifyDocs
import sys
import time

LOGFILE = cdr.DEFAULT_LOGDIR + "/ocecdr-4047.log"

class Control:
    MAP = {
        "about iact - patient summary": "About CAM - IACT Patient summary",
        "for more information - cam summary":
        "For more information - IACT summary",
        "to learn more - cam patient summary":
        "To learn more - IACT patient summary",
        "questions about cam - patient summary":
        "Questions about CAM - IACT Patient summary"
    }
    def __init__(self):
        self.start = time.time()
        cursor = cdrdb.connect("CdrGuest").cursor()
        cursor.execute("""\
SELECT doc_id, value
  FROM query_term
 WHERE path = '/MiscellaneousDocument/MiscellaneousDocumentMetadata'
            + '/MiscellaneousDocumentType'
   AND value LIKE '% cam %'
    OR value = 'about iact - patient summary'""")
        rows = cursor.fetchall()
        self.ids = [row[0] for row in rows if row[1].lower() in self.MAP]
    def getDocIds(self):
        return sorted(self.ids)
    def run(self, docObj):
        root = etree.XML(docObj.xml)
        for node in root.findall("MiscellaneousDocumentMetadata"
                                 "/MiscellaneousDocumentType"):
            if node.text is not None and node.text.lower() in self.MAP:
                node.text = self.MAP[node.text.lower()]
        return etree.tostring(root, encoding="utf-8", xml_declaration=True)

#----------------------------------------------------------------------
# Create the job object and run the job.
#----------------------------------------------------------------------
if len(sys.argv) < 3 or sys.argv[2] not in ('test', 'live'):
    sys.stderr.write("usage: ocecdr-4047.py session test|live\n")
    sys.exit(1)
obj = Control()
testMode = sys.argv[2] == 'test'
cdr.logwrite("running in %s mode" % sys.argv[2], LOGFILE)
job = ModifyDocs.Job(sys.argv[1], "", obj, obj,
                     "Change CAM misc doc type names (OCECDR-4047)",
                     testMode=testMode, logFile=LOGFILE)
job.run()
cdr.logwrite("elapsed: %s seconds" % (obj.start - time.time()))
