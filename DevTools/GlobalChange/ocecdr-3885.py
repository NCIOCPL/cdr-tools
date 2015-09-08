#----------------------------------------------------------------------
#
# $Id$
#
# Summary enhancements for NLM
#
# JIRA::OCECDR-3885
#
#----------------------------------------------------------------------
import cdr
import ModifyDocs
import lxml.etree as etree
import cdrdb
import re
import sys

def get_stripped_text(node):
    if node is None or node.text is None:
        return None
    value = node.text.strip()
    return value or None

class Control:
    topic_paths = (
        "SummaryMetaData/MainTopics/Term",
        "SummaryMetaData/SecondaryTopics/Term"
        )
    terms = {}
    paragraphs = {
        "Health professionals": [
            ("This PDQ cancer information summary for health professionals "
             "provides comprehensive, peer-reviewed, evidence-based informa"
             "tion about @@PURPOSE TEXT@@. It is intended as a resource to "
             "inform and assist clinicians who care for cancer patients. It"
             " does not provide formal guidelines or recommendations for ma"
             "king health care decisions."),
            ("This summary is reviewed regularly and updated as necessary b"
             "y the @@BOARD NAME@@, which is editorially independent of the"
             " National Cancer Institute (NCI). The summary reflects an ind"
             "ependent review of the literature and does not represent a po"
             "licy statement of NCI or the National Institutes of Health (N"
             "IH).")
        ],
        "Patients": [
            ("This PDQ cancer information summary has current information a"
             "bout @@PURPOSE TEXT@@. It is meant to inform and help patient"
             "s, families, and caregivers. It does not give formal guidelin"
             "es or recommendations for making decisions about health care."),
            ("Editorial Boards write the PDQ cancer information summaries "
             "and keep them up to date. These Boards are made up of expert"
             "s in cancer treatment and other specialties related to cance"
             "r. The summaries are reviewed regularly and changes are made"
             " when there is new information. The date on each summary (\""
             "Date Last Modified\") is the date of the most recent change."
             " The information in this patient summary was taken from the "
             "health professional version, which is reviewed regularly and"
             " updated as needed, by the @@BOARD NAME@@.")
        ],
    }
    def __init__(self):
        self.cursor = cdrdb.connect("CdrGuest").cursor()
        query = cdrdb.Query("query_term", "doc_id")
        query.where(query.Condition("path", "/Summary/@ModuleOnly"))
        query.where(query.Condition("value", "Yes"))
        rows = query.execute(self.cursor).fetchall()
        module_only = set([row[0] for row in rows])
        query = cdrdb.Query("active_doc d", "d.id")
        query.join("doc_type t", "t.id = d.doc_type")
        query.where(query.Condition("t.name", "Summary"))
        #query.limit(5)
        rows = query.execute(self.cursor).fetchall()
        self.doc_ids = [row[0] for row in rows if row[0] not in module_only]
    def get_term_name(self, node):
        ref = node.get("{cips.nci.nih.gov/cdr}ref")
        if not ref:
            return None
        term_id = re.sub(r"[^\d]+", "", ref)
        if term_id not in Control.terms:
            query = cdrdb.Query("query_term", "value")
            query.where(query.Condition("path", "/Term/PreferredName"))
            query.where(query.Condition("doc_id", term_id))
            rows = query.execute(self.cursor).fetchall()
            if not rows:
                return None
            value = rows[0][0].strip()
            if not value:
                return None
            Control.terms[term_id] = value
        return Control.terms[term_id]
    def get_english_summary(self, root):
        ref = root.find("TranslationOf").get("{cips.nci.nih.gov/cdr}ref")
        doc_id = re.sub(r"[^\d]+", "", ref)
        query = cdrdb.Query("document", "xml")
        query.where(query.Condition("id", doc_id))
        rows = query.execute(self.cursor).fetchall()
        if not rows:
            raise Exception("can't find English summary %s" % repr(ref))
        return etree.XML(rows[0][0].encode("utf-8"))
    def make_abstract(self, root):
        purpose = "*** UNSPECIFIED PURPOSE TEXT ***"
        board_name = "*** UNSPECIFIED BOARD NAME ***"
        language = root.find("SummaryMetaData/SummaryLanguage").text
        audience = root.find("SummaryMetaData/SummaryAudience").text
        if language != "English":
            root = self.get_english_summary(root)
        value = get_stripped_text(root.find("SummaryMetaData/PurposeText"))
        if value:
            purpose = value
        for node in root.findall("SummaryMetaData/PDQBoard/Board"):
            value = get_stripped_text(node)
            if value and "Advisory" not in value:
                board_name = value
        paragraphs = Control.paragraphs[audience]
        abstract = etree.Element("SummaryAbstract")
        para = paragraphs[0].replace("@@PURPOSE TEXT@@", purpose)
        etree.SubElement(abstract, "Para").text = para
        para = paragraphs[1].replace("@@BOARD NAME@@", board_name)
        etree.SubElement(abstract, "Para").text = para
        return abstract
    def getDocIds(self):
        return self.doc_ids
    def run(self, doc_object):
        try:
            tree = etree.XML(doc_object.xml)
            meta_data = tree.find("SummaryMetaData")
            for node in meta_data.findall("SummaryAbstract"):
                return doc_object.xml # don't modify document twice
            meta_data.append(self.make_abstract(tree))
            keywords = set()
            for path in Control.topic_paths:
                for node in tree.findall(path):
                    keyword = self.get_term_name(node)
                    if keyword:
                        keywords.add(keyword)
            if keywords:
                wrapper = etree.SubElement(meta_data, "SummaryKeyWords")
                for keyword in keywords:
                    etree.SubElement(wrapper, "SummaryKeyWord").text = keyword
            return etree.tostring(tree)
        except Exception, e:
            try:
                self.job.log("failure: %s" % e)
            except:
                pass
            return doc_object.xml

if len(sys.argv) != 4 or sys.argv[3] not in ("test", "live"):
    sys.stderr.write("usage: %s uid pwd test|live\n" % sys.argv[0])
    sys.exit(1)
uid, pwd, flag = sys.argv[1:]
test_mode = flag == "test"
control = Control()
if not pwd:
    uid = cdr.login(uid, "")
job = ModifyDocs.Job(uid, pwd, control, control,
                     "Enhance Summary for NLM (JIRA::OCECDR-3885)",
                     validate=True, testMode=test_mode)
control.job = job
job.run()
