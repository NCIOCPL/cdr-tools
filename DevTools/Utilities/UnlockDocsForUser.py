#!/usr/bin/env python

"""Unlock all documents checked out by a user.
"""

from argparse import ArgumentParser
from getpass import getpass
from sys import stderr
from cdr import login, unlock
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
        err = unlock(opts.session, row.id, tier=opts.tier, reason=COMMENT)
        if err:
            stderr.write(f"Failure unlocking CDR{row.id:010d}: {err}\n")
        else:
            print(f"unlocked CDR{row.id:010d}")
