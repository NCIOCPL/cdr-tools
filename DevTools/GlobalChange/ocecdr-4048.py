#----------------------------------------------------------------------
#
# $Id$
#
# Global change to add PubmedIDs to the Summary documents.
#
# JIRA::OCECDR-4048
#
#----------------------------------------------------------------------
import cdr
import lxml.etree as etree
import ModifyDocs
import sys
import time

LOGFILE = cdr.DEFAULT_LOGDIR + "/ocecdr-4048.log"

class PubmedBookArticle:
    def __init__(self, node):
        self.cdr_id = self.pubmed_id = None
        nodes = node.findall("BookDocument/PMID")
        if len(nodes) != 1:
            raise Exception("%d PMID nodes" % len(nodes))
        self.pubmed_id = nodes[0].text.strip()
        if len(self.pubmed_id) != 8:
            raise Exception("funky PMID %s" % repr(self.pubmed_id))
        nodes = node.findall("BookDocument/ArticleTitle")
        if len(nodes) != 1:
            raise Exception("%d ArticleTitle nodes" % len(nodes))
        if nodes[0].get("book") != "pdqcis":
            raise Exception("%s not pdqcis" % self.pubmed_id)
        part = nodes[0].get("part")
        if not part or not part.startswith("CDR"):
            raise Exception("%s has no CDR ID" % self.pubmed_id)
        try:
            self.cdr_id = int(part[3:])
        except:
            raise Exception("funky CDR ID %s" % repr(part))


class Control:
    def __init__(self):
        self.start = time.time()
        self.pmids = {}
        tree = etree.parse("PDQ_Summaries_PMID.xml")
        for node in tree.getroot().findall("PubmedBookArticle"):
            pba = PubmedBookArticle(node)
            self.pmids[pba.cdr_id] = pba.pubmed_id
    def getDocIds(self):
        return sorted(self.pmids)
    def run(self, docObj):
        root = etree.XML(docObj.xml)
        cdr_id = cdr.exNormalize(docObj.id)[1]
        meta_data = root.find("SummaryMetaData")
        nodes = meta_data.findall("PMID")
        if len(nodes) > 1:
            raise Exception("%d PMID elements" % len(nodes))
        if len(nodes) == 1:
            nodes[0].text = self.pmids[cdr_id]
        else:
            etree.SubElement(meta_data, "PMID").text = self.pmids[cdr_id]
        return etree.tostring(root, encoding="utf-8", xml_declaration=True)

#----------------------------------------------------------------------
# Create the job object and run the job.
#----------------------------------------------------------------------
if len(sys.argv) < 3 or sys.argv[2] not in ('test', 'live'):
    sys.stderr.write("usage: ocecdr-4048.py session test|live\n")
    sys.exit(1)
control = Control()
testMode = sys.argv[2] == 'test'
cdr.logwrite("running in %s mode" % sys.argv[2], LOGFILE)
job = ModifyDocs.Job(sys.argv[1], "", control, control,
                     "Populate PMID element in summaries (OCECDR-4048)",
                     testMode=testMode, logFile=LOGFILE)
job.run()
cdr.logwrite("elapsed: %s seconds" % (control.start - time.time()))
