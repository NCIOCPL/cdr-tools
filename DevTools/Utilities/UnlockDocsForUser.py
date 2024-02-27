#!/usr/bin/env python

"""Unlock all documents checked out by a user.
"""

from argparse import ArgumentParser
from sys import stderr
from cdr import unlock
from cdrapi import db

COMMENT = "Unlocked by UnlockDocsForUser script"

parser = ArgumentParser()
parser.add_argument("user")
parser.add_argument("--tier")
parser.add_argument("--session", required=True)
opts = parser.parse_args()
cursor = db.connect(user="CdrGuest", tier=opts.tier).cursor()
query = db.Query("checkout c", "c.id").unique()
query.join("open_usr u", "u.id = c.usr")
query.where("c.dt_in IS NULL")
query.where(query.Condition("u.name", opts.user))
rows = query.execute(cursor).fetchall()
print(f"unlocking {len(rows):d} documents")
if rows:
    for row in rows:
        try:
            unlock(opts.session, row.id, tier=opts.tier, reason=COMMENT)
            print(f"unlocked CDR{row.id:010d}")
        except Exception as e:
            stderr.write(f"Failure unlocking CDR{row.id:010d}: {e}\n")
