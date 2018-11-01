#!/usr/bin/env python
#----------------------------------------------------------
# Reindex all documents of a given doctype.
#----------------------------------------------------------
import argparse
import cdr
from cdrapi import db as cdrdb
from cdrapi.settings import Tier

parser = argparse.ArgumentParser()
parser.add_argument("doctype")
parser.add_argument("--max-docs", type=int)
parser.add_argument("--tier")
opts = parser.parse_args()
cursor = cdrdb.connect(user="CdrGuest", tier=opts.tier).cursor()
query = cdrdb.Query("document d", "d.id")
query.join("doc_type t", "t.id = d.doc_type")
query.where(query.Condition("t.name", opts.doctype))
if opts.max_docs:
    query.limit(opts.max_docs)
rows = query.order("d.id").execute(cursor).fetchall()
where = opts.tier if opts.tier else Tier().name
print("reindexing {} documents on {}".format(len(rows), where))
for doc_id, in rows:
    print("reindexing CDR%010d" % doc_id)
    resp = cdr.reindex("guest", doc_id, tier=opts.tier)
    if resp: print resp
