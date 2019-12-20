#!/usr/bin/env python

"""Check for English summaries on the CMS for publishable Spanish translations.
"""

from argparse import ArgumentParser
from cdrapi import db
from cdrapi.publishing import DrupalClient
from cdrapi.users import Session

parser = ArgumentParser()
parser.add_argument("--tier")
parser.add_argument("--cms")
opts = parser.parse_args()
cursor = db.connect(user="CdrGuest", tier=opts.tier).cursor()
query = db.Query("query_term_pub t", "t.doc_id", "t.int_val", "e.id")
query.join("pub_proc_cg s", "s.id = t.doc_id")
query.outer("pub_proc_cg e", "e.id = t.int_val")
query.where("t.path = '/Summary/TranslationOf/@cdr:ref'")
rows = query.execute(cursor).fetchall()
for es, en, published in rows:
    if not published:
        print(f"CDR{es} is translation of unpublished CDR{en}")
client = DrupalClient(Session("guest"), base=opts.cms)
catalog = client.list()
on_cms = set([summary.cdr_id for summary in catalog])
for es, en, published in rows:
    if en not in on_cms:
        print(f"CDR{es} is translation of CDR{en} which is not on the CMS")
