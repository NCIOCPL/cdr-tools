"""Fetch the current FileSweeper configuration.
"""

from argparse import ArgumentParser
from sys import stdout
from lxml import etree
from cdrapi import db

# Find out what we're supposed to do
parser = ArgumentParser()
parser.add_argument("--tier", "-t")
parser.add_argument("--raw", "-r", action="store_true")
opts = parser.parse_args()

# Fetch the XML document
cursor = db.connect(user="CdrGuest", tier=opts.tier).cursor()
query = db.Query("document d", "d.id", "d.xml")
query.join("doc_type t", "t.id = d.doc_type")
query.where("t.name = 'SweepSpecifications'")
rows = query.execute(cursor).fetchall()
if len(rows) > 1:
    ids = ", ".join([f"CDR{row.id}" for row in rows])
    raise Exception(f"Multiple spec docs: {ids}")
if not rows:
    raise Exception("No sweep specification document found")
xml = rows[0].xml
print(rows[0].id)
# Print it
if opts.raw:
    stdout.buffer.write(xml.encode("utf-8"))
else:
    root = etree.fromstring(xml.encode("utf-8"))
    xml = etree.tostring(root, pretty_print=True, encoding="utf-8")
    stdout.buffer.write(xml)
