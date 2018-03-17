#!/usr/bin/env python

"""
Save the configuration for the file sweeper job
"""

import argparse
import cdr

# Find out what we're supposed to do
parser = argparse.ArgumentParser()
parser.add_argument("filepath")
parser.add_argument("--tier", "-t")
parser.add_argument("--comment", "-c")
parser.add_argument("--session", "-s", required=True)
opts = parser.parse_args()

# Load the XML document
with open(opts.filepath) as fp:
    xml = fp.read()
if "]]>" in xml:
    parser.error("CdrDoc wrapper must be stripped from the file")

# Prepare the save operation
save_opts = dict(
    checkIn="Y",
    reason=opts.comment,
    comment=opts.comment,
    ver="Y",
    val="Y",
    tier=opts.tier,
    showWarnings=True
)

# See if we already have the document installed
doctype = "SweepSpecifications"
query = "CdrCtl/Title contains %"
result = cdr.search("guest", query, doctypes=[doctype], tier=opts.tier)
if len(result) > 1:
    raise Exception("Can't have more than one sweep spec document")

# If the document already exists, create a new version
if result:
    doc_id = result[0].docId
    args = dict(checkout="Y", getObject=True, tier=opts.tier)
    doc = cdr.getDoc(opts.session, doc_id, **args)
    error_message = cdr.checkErr(doc)
    if error_message:
        parser.error(error_message)
    doc.xml = xml
    save_opts["doc"] = str(doc)
    doc_id, warnings = cdr.repDoc(opts.session, **save_opts)

# Otherwise, create the document (with a first version)
else:
    doc = cdr.Doc(xml, doctype, encoding="utf-8")
    save_opts["doc"] = str(doc)
    doc_id, warnings = cdr.addDoc(opts.session, **save_opts)

# Let the user know how things went
if warnings:
    print(doc_id and "WARNINGS" or "ERRORS")
    for error in cdr.getErrors(warnings, asSequence=True):
        print(" -->", error)
if not doc_id:
    print("*** DOCUMENT NOT SAVED ***")
else:
    versions = cdr.lastVersions(opts.session, doc_id, tier=opts.tier)
    print("Saved {} as version {}".format(doc_id, versions[0]))
