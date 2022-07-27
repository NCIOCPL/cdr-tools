#!/usr/bin/env python

"""Report counts for unique values in cdr:id attributes in a CDR document.
"""

from argparse import ArgumentParser
from cdrapi.docs import Doc
from cdrapi.users import Session

CDR_ID = Doc.qname("id")

parser = ArgumentParser()
parser.add_argument("doc_id")
parser.add_argument("--threshold", type=int, default=0)
opts = parser.parse_args()
doc = Doc(Session("guest"), id=opts.doc_id)
ids = {}
for node in doc.root.xpath("//*[@cdr:id]", namespaces=Doc.NSMAP):
    value = node.get(CDR_ID)
    ids[value] = ids.get(value, 0) + 1
for value, count in sorted(ids.items()):
    if count > opts.threshold:
        print(f"{count:d}, {value}")
