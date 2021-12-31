#!/usr/bin/env python
"""
Program to replace a schema in the CDR database with a version found in
a file, typically a file in a version control sandbox.

Versions in the file should not have CdrDoc wrappers.  The wrapper is added
by this program.

Matching is done by searching the database for the name of the file, e.g.,
'SummarySchema.xml,' matching it against the title of the document
in the database version of the document.  That title is created by
this UpdateSchemas.py program - which should always be used when a schema
update is required.

If no match is found, we assume that the schema in the file is new.  It will
be inserted into the database as a new schema document.
"""

import argparse
from getpass import getpass
from glob import glob
import os
import sys
from cdrapi.docs import Doc
from cdrapi.users import Session
from cdrapi.db import Query

# Collect the command-line arguments
parser = argparse.ArgumentParser()
parser.add_argument("schemas", nargs="+")
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("--user")
group.add_argument("--session")
opts = parser.parse_args()
if opts.user:
    try:
        session = Session.create_session(opts.user)
    except Exception:
        password = getpass()
        try:
            session = Session.create_session(opts.user, password=password)
        except Exception:
            print("invalid credentials")
            sys.exit(1)
else:
    session = Session(opts.session)

# Stepping through the command line arguments (i.e. schema files)
# for processing
# If the schema doesn't exist in the CDR it will be added,
# otherwise the existing schema file will be replaced.
# --------------------------------------------------------------
for token in opts.schemas:
    schemas = glob(token)
    if not schemas:
        print("%s not found" % token)
        sys.exit(1)

    for schema in schemas:
        xml = open(schema).read()
        title = os.path.basename(schema)
        query = Query("document d", "d.id")
        query.join("doc_type t", "t.id = d.doc_type")
        query.where(query.Condition("d.title", title))
        query.where("t.name = 'schema'")
        row = query.execute().fetchone()
        print("schema: %s" % schema)
        if not row:
            verb = "added"
            doc = Doc(session, xml=xml)
        else:
            verb = "updated"
            doc = Doc(session, xml=xml, id=row.id)
            try:
                doc.check_out()
            except Exception as e:
                print(("{}: {}".format(doc.cdr_id, e)))
                continue
        try:
            doc.save(title=title, unlock=True, version=True)
            print(("{} {}".format(verb, doc.cdr_id)))
        except Exception as e:
            print(("{}: {}".format(doc.cdr_id, e)))

# Close the session if we created it here.
if opts.user:
    session.logout()
