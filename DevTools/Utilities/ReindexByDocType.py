#!/usr/bin/env python
#----------------------------------------------------------
# Reindex all documents of a given doctype.
#----------------------------------------------------------
import argparse
import cdr
import cdrdb

parser = argparse.ArgumentParser()
parser.add_argument("doctype")
parser.add_argument("--max-docs", type=int)
parser.add_argument("--tier")
opts = parser.parse_args()
query = cdrdb.Query("document d", "d.id")
query.join("doc_type t", "t.id = d.doc_type")
query.where(query.Condition("t.name", opts.doctype))
if opts.max_docs:
    query.limit(opts.max_docs)
rows = query.order("d.id").execute().fetchall()
print("reindexing {} documents".format(len(rows)))
for doc_id, in rows:
    print("reindexing CDR%010d" % doc_id)
    resp = cdr.reindex("guest", doc_id, tier=opts.tier)
    if resp: print resp
