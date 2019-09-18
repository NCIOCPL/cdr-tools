#!/usr/bin/env python
#----------------------------------------------------------
# Regenerate and update document table titles for all docs of a
# given doctype.
#----------------------------------------------------------

from argparse import ArgumentParser
import time
import cdr
from cdrapi import db

parser = ArgumentParser()
parser.add_argument("--doctype", required=True)
parser.add_argument("--max-docs", type=int)
parser.add_argument("--tier")
opts = parser.parse_args()
cursor = db.connect(user="CdrGuest", tier=opts.tier).cursor()
query = db.Query("document d", "d.id").order("d.id")
query.join("doc_type t", "t.id = d.doc_type")
query.where(query.Condition("t.name", opts.doctype))
if opts.max_docs is not None:
    query.limit(opts.max_docs)
rows = query.execute(cursor).fetchall()
print(f"reindexing {len(rows):d} documents")
count = 0
for row in rows:
    print(f"Updating title for CDR{row.id:010d}", end="")
    resp = cdr.updateTitle("guest", row.id, tier=opts.tier)
    if resp:
        print(" - changed", flush=True)
    else:
        print(" - no change needed", flush=True)

    # Pause every so many docs (to avoid swamping the machine or sshd)
    # We had a problem at one time that this fixed - though it may
    #   not be needed any more
    count += 1
    if count % 50 == 0:
        time.sleep(1)
