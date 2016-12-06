#----------------------------------------------------------------------
# Find trials documents which need to be blocked because the trials
# they represent are not included in the set of clinical_trial documents
# fetched from CTRP. Run this after the first CTGovDownload job which
# connects to CTRP instead of NLM. Log information is written to the
# standard output. The list of document IDs for the documents which
# need to be blocked is written to obsolete-trials-to-drop.txt. This
# file is used in turn by the block-obsolete-trial-docs.py (q.v.).
# Part of the Egyptian Mau release, which includes the redesigned
# Clinical Trial Search software.
#----------------------------------------------------------------------
import cdrdb
import datetime
import lxml.etree as etree
import sys
import zipfile
import requests

FILENAME  = "CTRP-TO-CANCER-GOV-EXPORT-%s.zip"
BASE      = "https://trials.nci.nih.gov/pa/pdqgetFileByDate.action"

class TrialSet:
    def __init__(self):
        cursor.execute("""\
SELECT nlm_id, cdr_id
  FROM ctgov_import
 WHERE cdr_id IS NOT NULL
   AND xml IS NOT NULL""")
        self.id_map = {} #trial_ids = {}
        for nct_id, cdr_id in cursor.fetchall():
            self.id_map[nct_id.strip().upper()] = cdr_id
        date = len(sys.argv) > 1 and sys.argv[1] or datetime.date.today()
        filename = FILENAME % date
        if not zipfile.is_zipfile(filename):
            url = "%s?date=%s" % (BASE, filename)
            response = requests.get(url)
            doc = response.content
            code = response.status_code
            if code != 200:
                raise Exception("%s HTTP code %s" % (url, code))
            fp = open(filename, "wb")
            fp.write(doc)
            fp.close()
        if not zipfile.is_zipfile(filename):
            raise Exception("%s is not a ZIP file" % filename)
        self.zf = zipfile.ZipFile(filename)
        self.names = self.zf.namelist()
        self.trials = {} # ctrp_trials = set()
        for name in self.names:
            xml = self.zf.read(name)
            nct_id = TrialSet.get_nct_id(xml)
            if not nct_id or not nct_id.strip():
                print "%s HAS NO NCT ID" % name
            else:
                if nct_id != name.upper()[:-4]:
                    print "%s HAS NCT ID %s" % (name, nct_id)
                if nct_id in self.trials:
                    print "%s IN CTRP SET MORE THAN ONCE" % nct_id
                else:
                    self.trials[nct_id] = self.id_map.get(nct_id)
    @staticmethod
    def get_nct_id(xml):
        tree = etree.XML(xml)
        for node in tree.findall("id_info/nct_id"):
            if node.text is not None:
                return node.text.upper().strip()

cursor = cdrdb.connect("CdrGuest").cursor()
trial_set = TrialSet()
fp = open("obsolete-trials-to-drop.txt", "w")
cursor.execute("""\
SELECT d.id
  FROM active_doc d
  JOIN doc_type t
    ON t.id = d.doc_type
 WHERE t.name = 'InScopeProtocol'""")
for row in cursor.fetchall():
    print "BLOCKING INSCOPE PROTOCOL DOCUMENT CDR%d" % row[0]
    fp.write("%d\n" % row[0])
cursor.execute("""\
SELECT d.id
  FROM active_doc d
  JOIN doc_type t
    ON t.id = d.doc_type
 WHERE t.name = 'CTGovProtocol'""")
ctgov_doc_ids = [row[0] for row in cursor.fetchall()]
for doc_id in ctgov_doc_ids:
    cursor.execute("""\
SELECT value
  FROM query_term
 WHERE path = '/CTGovProtocol/IDInfo/NCTID'
   AND doc_id = ?""", doc_id)
    rows = cursor.fetchall()
    if rows:
        nct_id = rows[0][0].strip().upper()
        if nct_id not in trial_set.trials:
            fp.write("%d\n" % doc_id)
            print "DROPPING NLM TRIAL CDR%d (%s, NOT IN CTRP SET)" % (
                doc_id, nct_id)
            cursor.execute("""\
SELECT dt, cdr_id, comment, dropped, reason_dropped, force
  FROM ctgov_import
 WHERE nlm_id = ?""", nct_id)
            for row in cursor.fetchall():
                print "\t%s" % repr(row)
        else:
            mapped_id = trial_set.trials[nct_id]
            if doc_id != mapped_id:
                print "DROPPING CDR%d (%s IS MAPPED TO %s)" % (doc_id, nct_id,
                                                               mapped_id)
                fp.write("%d\n" % doc_id)
    else:
        print "DROPPING CTGOV PROTOCOL DOCUMENT CDR%d (NO NCT ID)" % doc_id
        fp.write("%d\n" % doc_id)
fp.close()
