#!/usr/bin/env python

"""
Reindex all documents of a given doctype.
"""

import argparse
from sys import stderr
import cdr
from cdrapi import db as cdrdb
from cdrapi.settings import Tier

parser = argparse.ArgumentParser()
parser.add_argument("doctype")
parser.add_argument("--max-docs", type=int)
parser.add_argument("--tier")
parser.add_argument("--skip", type=int)
opts = parser.parse_args()
cursor = cdrdb.connect(user="CdrGuest", tier=opts.tier).cursor()
query = cdrdb.Query("document d", "d.id")
query.join("doc_type t", "t.id = d.doc_type")
query.where(query.Condition("t.name", opts.doctype))
if opts.max_docs:
    query.limit(opts.max_docs)
rows = query.order("d.id").execute(cursor).fetchall()
if opts.skip:
    rows = rows[opts.skip:]
where = opts.tier if opts.tier else Tier().name
stderr.write("reindexing {} documents on {}\n".format(len(rows), where))
count = 0
for doc_id, in rows:
    count += 1
    args = doc_id, count, len(rows)
    stderr.write("\rreindexing CDR{:010d} {:d} of {:d}".format(*args))
    resp = cdr.reindex("guest", doc_id, tier=opts.tier)
    if resp:
        stderr.write("\n{!r}\n".format(resp))
stderr.write("\n")
