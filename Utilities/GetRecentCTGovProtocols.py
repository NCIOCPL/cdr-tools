#----------------------------------------------------------------------
# $Id$
#
# Find the latest trial documents in the ClinicalTrials.gov database
# which are relevant to cancer and record them in the CDR database.
# Optional command-line argument can be given to specify how far back
# to go for trials (using ISO format YYYY-MM-DD). Defaults to 8 days
# before the latest first_received value in the ctgov_trial table,
# or 2015-01-01, if the table is empty (that is, we're running for
# the first time).
#
# JIRA::OCECDR-3877
#----------------------------------------------------------------------
import cdr
import cdrdb
import datetime
import lxml.etree as etree
import sys
import urllib2
import zipfile

LOGFILE = cdr.DEFAULT_LOGDIR + "/RecentCTGovProtocols.log"
ZIPFILE = cdr.BASEDIR + "/Output/RecentCTGovProtocols.zip"

#----------------------------------------------------------------------
# Get stripped text content from a node. Assumes no mixed content.
#----------------------------------------------------------------------
def get_stripped_text(node):
    if node is not None and node.text is not None:
        return node.text.strip()
    return None

#----------------------------------------------------------------------
# Object holding information about a single clinical_trial document.
#----------------------------------------------------------------------
class Trial:
    def __init__(self, xml):
        root = etree.XML(xml)
        self.nct_id = self.first_received = None
        self.sponsors = []
        self.other_ids = []
        for node in root.findall("id_info/*"):
            value = get_stripped_text(node)
            if value:
                if node.tag == "nct_id":
                    self.nct_id = value
                elif node.tag in ("org_study_id", "secondary_id"):
                    self.other_ids.append(value)
        self.title = get_stripped_text(root.find("brief_title"))
        if not self.title:
            self.title = get_stripped_text(root.findall("official_title"))
        value = get_stripped_text(root.find("firstreceived_date"))
        if value:
            dt = datetime.datetime.strptime(value, "%B %d, %Y")
            self.first_received = dt.date()
        self.phase = get_stripped_text(root.find("phase"))
        for node in root.findall("sponsors/*/agency"):
            value = get_stripped_text(node)
            if value:
                self.sponsors.append(value)

#----------------------------------------------------------------------
# Fetch the cancer trials added since a certain point in time.
#----------------------------------------------------------------------
def fetch(since):
    cdr.logwrite("fetching trials added on or after %s" % since, LOGFILE)
    conditions = ['cancer', 'lymphedema', 'myelodysplastic syndromes',
                  'neutropenia', 'aspergillosis', 'mucositis']
    diseases = ['cancer', 'neoplasm']
    sponsor = "(National Cancer Institute) [SPONSOR-COLLABORATORS]"
    conditions = "(%s) [CONDITION]" % " OR ".join(conditions)
    diseases = "(%s) [DISEASE]" % " OR ".join(diseases)
    term = "term=%s OR %s OR %s" % (conditions, diseases, sponsor)
    cutoff = since.strftime("&rcv_s=%m/%d/%Y")
    params = "%s%s&studyxml=true" % (term, cutoff)
    params = params.replace(" ", "+")
    base  = "http://clinicaltrials.gov/ct2/results"
    url = "%s?%s" % (base, params)
    cdr.logwrite(url, LOGFILE)
    try:
        urlobj = urllib2.urlopen(url)
        page   = urlobj.read()
    except Exception, e:
        error = "Failure downloading trial set using %s: %s" % (url, e)
        raise Exception(error)
    fp = open(ZIPFILE, "wb")
    fp.write(page)
    fp.close()

#----------------------------------------------------------------------
# Parse the trial documents and record the ones we don't already have.
#----------------------------------------------------------------------
def load():
    cursor.execute("SELECT nct_id FROM ctgov_trial")
    nct_ids = set([row[0].upper() for row in cursor.fetchall()])
    zf = zipfile.ZipFile(ZIPFILE)
    names = zf.namelist()
    loaded = 0
    for name in names:
        try:
            xml = zf.read(name)
            trial = Trial(xml)
            if trial.nct_id and trial.nct_id.upper() not in nct_ids:
                nct_ids.add(trial.nct_id.upper())
                cursor.execute("""\
INSERT INTO ctgov_trial (nct_id, trial_title, trial_phase, first_received)
     VALUES (?, ?, ?, ?)""", (trial.nct_id, trial.title[:1024],
                              trial.phase and trial.phase[:20] or None,
                              trial.first_received))
                position = 1
                for other_id in trial.other_ids:
                    cursor.execute("""\
INSERT INTO ctgov_trial_other_id (nct_id, position, other_id)
     VALUES (?, ?, ?)""", (trial.nct_id, position, other_id[:1024]))
                    position += 1
                position = 1
                for sponsor in trial.sponsors:
                    cursor.execute("""\
INSERT INTO ctgov_trial_sponsor (nct_id, position, sponsor)
     VALUES (?, ?, ?)""", (trial.nct_id, position, sponsor[:1024]))
                    position += 1
                conn.commit()
                loaded += 1
        except Exception, e:
            cdr.logwrite("%s: %s" % (name, e), LOGFILE)
    cdr.logwrite("processed %d trials, %d new" % (len(names), loaded), LOGFILE)

#----------------------------------------------------------------------
# Figure out how far back to go.
#----------------------------------------------------------------------
def get_cutoff():
    if len(sys.argv) > 1:
        return datetime.datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
    cursor.execute("SELECT MAX(first_received) FROM ctgov_trial")
    rows = cursor.fetchall()
    if rows and rows[0][0]:
        last = datetime.datetime.strptime(rows[0][0][:10], "%Y-%m-%d")
        return (last - datetime.timedelta(8)).date()
    else:
        return datetime.date(2015, 1, 1)

#----------------------------------------------------------------------
# Run the job if loaded as a script (not a module).
#----------------------------------------------------------------------
if __name__ == "__main__":
    try:
        conn = cdrdb.connect()
        cursor = conn.cursor()
        cutoff = get_cutoff()
        fetch(cutoff)
        load()
    except Exception, e:
        cdr.logwrite("Failure: %s" % e, LOGFILE, True, True)
