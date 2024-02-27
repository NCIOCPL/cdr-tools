#!/usr/bin/env python3
# ----------------------------------------------------------------------
#
# Command-line script to list filters by name with file names based
# on PROD CDR IDs.  Useful for finding a CDR filter in a git working
# directory.
#
# ----------------------------------------------------------------------

from cdrapi import db

cursor = db.connect(user='CdrGuest').cursor()
cursor.execute("""\
    SELECT d.id, d.title
      FROM document d
      JOIN doc_type t
        ON t.id = d.doc_type
     WHERE t.name = 'filter'
  ORDER BY d.title""")
for docId, docTitle in cursor.fetchall():
    print(f"CDR{docId:010d}.xml {docTitle}")
