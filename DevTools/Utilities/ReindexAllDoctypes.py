#!/usr/bin/env python
# Re-index all documents in one of the CDR databases.
#
# Reports to terminal every 100 docs, and reports total docs to be
# indexed and actually indexed.

import argparse
import cdrapi.db
import cdr

parser = argparse.ArgumentParser()
parser.add_argument("--tier", "-t")
opts = parser.parse_args()
query = cdrapi.db.Query("document", "id").order("id")
cursor = cdrapi.db.connect(tier=opts.tier).cursor()
doc_ids = [row[0] for row in query.execute(cursor).fetchall()]
done = 0
print "reindexing %d documents" % len(doc_ids)
for doc_id in doc_ids:
    try:
        cdr.reindex("guest", doc_id, tier=opts.tier)
    except Exception as e:
        print("CDR{}: {}".format(doc_id, e))
    done += 1
    if done % 100 == 0:
        message = "Completed {} docs, last doc processed = CDR{}"
        print(message.format(done, doc_id))
print("Completed reindex of {} total documents".format(done))
