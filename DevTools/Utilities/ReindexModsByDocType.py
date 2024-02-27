#!/usr/bin/env python3
# ----------------------------------------------------------
# Re-index all documents of some document type for which the document
# was saved in the last N days, where N is passed on the command line.
#
# A version of ReindexByDocType.py
# ----------------------------------------------------------

from argparse import ArgumentParser
from datetime import date, timedelta
from time import sleep
from cdr import reindex
from cdrapi import db

ACTIONS = "ADD DOCUMENT", "MODIFY DOCUMENT"

parser = ArgumentParser()
parser.add_argument("--doctype", required=True)
parser.add_argument("--days", type=int, default=7)
parser.add_argument("--tier")
opts = parser.parse_args()
earliest = date.today() - timedelta(opts.days)
cursor = db.connect(user="CdrGuest", tier=opts.tier).cursor()
query = db.Query("document d", "d.id").unique().order("d.id")
query.join("audit_trail a", "a.document = d.id")
query.join("doc_type t", "t.id = d.doc_type")
query.join("action v", "v.id = a.action")
query.where(query.Condition("v.name", ACTIONS, "IN"))
query.where(query.Condition("a.dt", earliest, ">="))
rows = query.execute(cursor).fetchall()
print(f"reindexing {len(rows):d} documents")
count = 0
for row in rows:
    print(f"reindexing CDR{row.id:010d}", flush=True)
    try:
        reindex("guest", row.id, tier=opts.tier)
    except Exception as e:
        print(e)

    # Pause every 50 docs (to avoid swallowing the machine? swamping sshd?)
    count += 1
    if count % 50 == 0:
        sleep(1)
