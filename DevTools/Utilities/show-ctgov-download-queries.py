#----------------------------------------------------------------------
# $Id$
# Erika and Bryan need to know what queries we send to ClinicalTrials.gov.
#----------------------------------------------------------------------
import cdrdb

conditions = ['cancer', 'lymphedema', 'myelodysplastic syndromes',
              'neutropenia', 'aspergillosis', 'mucositis']
diseases = ['cancer', 'neoplasm']
sponsor = "(National Cancer Institute) [SPONSOR-COLLABORATORS]"
conditions = "(%s) [CONDITION]" % " OR ".join(conditions)
diseases = "(%s) [DISEASE]" % " OR ".join(diseases)
params = "%s OR %s OR %s&studyxml=true" % (conditions, diseases, sponsor)
params = "term=%s" % params.replace(" ", "+")
base = "http://clinicaltrials.gov/ct2/results"
url = "%s?%s" % (base, params)
print url
query = cdrdb.Query("ctgov_import", "nlm_id").where("force = 'Y'")
forced_ids = [row[0] for row in query.execute().fetchall()]
params = "term=%s&studyxml=true" % "+OR+".join(forced_ids[:10])
url = "%s?%s" % (base, params)
print url
fp = open("forced-ctgov-trials.txt", "w")
for pmid in sorted(forced_ids):
    fp.write("%s\n" % pmid.strip())
fp.close()
