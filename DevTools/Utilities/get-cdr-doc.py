#!/usr/bin/env python3

"""Get the XML for a CDR document.

Doesn't include the CdrDoc wrapper which GetCdrDoc.cmd gets. Also handles
non-ASCII characters better than that tool, at least on Windows.

Sends the XML to stdout, encoded as UTF-8.
"""

from argparse import ArgumentParser
from cdrapi import db
from sys import stdout

parser = ArgumentParser()
parser.add_argument("--id", "-i", type=int, required=True)
parser.add_argument("--version", "-v", type=int)
opts = parser.parse_args()
table = "doc_version" if opts.version else "all_docs"
query = db.Query(table, "xml")
query.where(query.Condition("id", opts.id))
if opts.version:
    query.where(query.Condition("num", opts.version))
rows = query.execute().fetchall()
if not rows:
    raise Exception("document not found")
stdout.buffer.write(rows[0].xml.encode("utf-8"))
