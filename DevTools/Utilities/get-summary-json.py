#!/usr/bin/env python

"""Generate JSON suitable for pushing into a test Drupal server.
"""

from argparse import ArgumentParser
from datetime import datetime
from json import dump
from pathlib import Path
from sys import stderr
from cdrapi.users import Session
from cdrpub import Control
from cdrapi import db
from cdrapi.docs import Doc

FILTERS = dict(
    Summary="Cancer Information Summary for Drupal CMS",
    DrugInformationSummary="Drug Information Summary for Drupal CMS",
)
ASSEMBLE = dict(
    Summary=Control.assemble_values_for_cis,
    DrugInformationSummary=Control.assemble_values_for_dis,
)

# Collect the options for this run.
start = datetime.now()
parser = ArgumentParser()
parser.add_argument("--tier", help="publish from another tier")
opts = parser.parse_args()
session = Session("guest", tier=opts.tier)

# Identify the documents.
query = db.Query("document d", "d.id", "t.name")
query.join("doc_type t", "t.id = d.doc_type")
query.join("pub_proc_cg c", "c.id = d.id")
query.where("t.name in ('Summary', 'DrugInformationSummary')")
rows = query.execute(session.cursor).fetchall()

# Create the directories.
stamp = start.strftime("%Y%m%d%H%M%S")
top_directory = Path(f"summaries-{stamp}")
english_cis = top_directory / "Summary/English"
spanish_cis = top_directory / "Summary/Spanish"
dis = top_directory / "DrugInformationSummary"
english_cis.mkdir(parents=True)
spanish_cis.mkdir(parents=True)
dis.mkdir(parents=True)

# Load the XSL/T filters.
xsl = {}
for key, value in FILTERS.items():
    xsl[key] = Doc.load_single_filter(session, value)

# Walk through the documents.
done = 0
for doc_id, doc_type in rows:
    root = Control.fetch_exported_doc(session, doc_id, "pub_proc_cg")
    values = ASSEMBLE[doc_type](session, doc_id, xsl[doc_type], root)
    if doc_type == "Summary":
        directory = english_cis if values["language"] == "en" else spanish_cis
    else:
        directory = dis
    path = directory / f"{doc_id}.json"
    with path.open("w", encoding="utf-8") as fp:
        dump(values, fp, indent=2)
    done += 1
    stderr.write(f"\rfetched {done} of {len(rows)} summaries")
elapsed = datetime.now() - start
stderr.write(f"\nelapsed {elapsed}\n")
