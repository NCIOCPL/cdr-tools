#!/usr/bin/env python

"""
Generate the JSON serialization of a summary for the Drupal CMS.

Writes to standard output.
"""

from argparse import ArgumentParser
from json import dumps
from cdrapi.users import Session
from cdrapi.docs import Doc
from cdrpub import Control
from sys import stderr

FILTERS = dict(
    Summary="Cancer Information Summary for Drupal CMS",
    DrugInformationSummary="Drug Information Summary for Drupal CMS",
)
ASSEMBLE = dict(
    Summary=Control.assemble_values_for_cis,
    DrugInformationSummary=Control.assemble_values_for_dis,
)

# Collect the options for this run.
parser = ArgumentParser()
parser.add_argument("--tier", help="publish from another tier")
parser.add_argument("--id", type=int, help="CDR ID for Summary", required=True)
opts = parser.parse_args()


# Prepare the document.
session = Session("guest", tier=opts.tier)
doc = Doc(session, id=opts.id)
stderr.write(f"Fetching {doc.doctype.name} document {doc.cdr_id}\n")
root = Control.fetch_exported_doc(session, doc.id, "pub_proc_cg")
xsl = Doc.load_single_filter(session, FILTERS[doc.doctype.name])
values = ASSEMBLE[doc.doctype.name](session, doc.id, xsl, root)
print(dumps(values, indent=2), end='')
