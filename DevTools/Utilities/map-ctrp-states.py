#----------------------------------------------------------------------
# $Id$
# Generates the SQL queries needed to fill in mappings for state names
# found in CTRP clinical_trial documents. This needs to be run as part
# of the Egyptian Mau release, which includes the redesigned Clinical
# Trials Search software. Redirect the output to a file and run it
# (or, on the upper tiers, give it to CBIIT's Database Team to run it)
# under SQL Server.
#----------------------------------------------------------------------
import cdrdb

cursor = cdrdb.connect("CdrGuest").cursor()
def get_usage_id(usage):
    cursor.execute("SELECT id FROM external_map_usage WHERE name = ?", usage)
    usage_id = cursor.fetchall()[0][0]
    return usage_id

ctgov_state_mapping_usage = get_usage_id("CT.gov States")
canadian_mappings = {
    'AB': 43911,
    'Alberta': 43911,
    'British Columbia': 43912,
    'Manitoba': 43913,
    'New Brunswick': 43914,
    'Newfoundland': 43915,
    'Newfoundland and Labrador': 43915,
    'Nova Scotia': 43917,
    'Ontario': 43910,
    'Prince Edward Island': 43918,
    'QC': 43919,
    'Quebec': 43919,
    'Saskatchewan': 43920
}
cursor.execute("""\
SELECT s.doc_id, s.value
  FROM query_term s
  JOIN query_term c
    ON c.doc_id = s.doc_id
 WHERE s.path = '/PoliticalSubUnit/PoliticalSubUnitShortName'
   AND c.path = '/PoliticalSubUnit/Country/@cdr:ref'
   AND c.int_val = 43753""")
us_mappings = {}
for doc_id, value in cursor.fetchall():
    us_mappings[value] = doc_id
mappings = us_mappings.copy()
mappings.update(canadian_mappings)
for mapped_value, mapping_id in mappings.iteritems():
    cursor.execute("""\
SELECT id, doc_id
  FROM external_map
 WHERE usage = ?
   AND value = ?""", (ctgov_state_mapping_usage, mapped_value))
    rows = cursor.fetchall()
    if rows:
        row_id, mapped_id = rows[0]
        if mapped_id:
            if mapped_id == mapping_id:
                continue
                print "%s=%d: OK" % (mapped_value, mapped_id)
            else:
                print ("UPDATE external_map SET doc_id = %d WHERE id = %d" %
                       (mapping_id, row_id))
                continue
                print "%s MAPPED TO %d INSTEAD OF %d" % (mapped_value,
                                                         mapped_id,
                                                         mapping_id)
        else:
            print ("UPDATE external_map SET doc_id = %d WHERE id = %d" %
                   (mapping_id, row_id))
            continue
            print "%s=%d BUT MAPPING TABLE HAS NULL" % (mapped_value,
                                                        mapping_id)
    else:
        print ("INSERT INTO external_map (usage, value, doc_id, usr, last_mod) "
               "VALUES (%d, '%s', %d, 2, GETDATE())" %
               (ctgov_state_mapping_usage, mapped_value, mapping_id))
        continue
        cdr_id = "%s=%d BUT NOT IN MAPPING TABLE" % (mapped_value, mapping_id)
print "GO"
