#!/usr/bin/env python

"""Fetch a list of who can do what.
"""

from argparse import ArgumentParser
from cdrapi import db

FIELDS = "a.name AS ActionName", "g.name AS GroupName", "u.name AS UserName"

parser = ArgumentParser()
parser.add_argument("--pattern")
parser.add_argument("--tier")
opts = parser.parse_args()
cursor = db.connect(tier=opts.tier).cursor()
query = db.Query("usr u", *FIELDS).unique().order(1, 2, 3)
query.join("grp_usr gu", "gu.usr = u.id")
query.join("grp g", "g.id = gu.grp")
query.join("grp_action ga", "ga.grp = g.id")
query.join("action a", "a.id = ga.action")
if opts.pattern:
    query.where(query.Condition("a.name", opts.pattern, "LIKE"))
for row in query.execute(cursor).fetchall():
    print("\t".join(row))
