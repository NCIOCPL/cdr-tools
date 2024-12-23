#!/usr/bin/env python
# ---------------------------------------------------------------------
#
# Pulls control documents and tables which need to be preserved from the
# development server in preparation for refreshing the CDR database from
# the production server.  If the development server has any document
# types which don't exist at all and for which documents exist which need
# to be preserved, name those document types on the command line.
#
# Usage:
#   PullDevData.py [newdoctype [newdoctype ...] ]
#
# ---------------------------------------------------------------------

import datetime
import os
import re
import sys
import time
from cdr import run_command
from cdrapi import db
from pathlib import Path

DUMP_JOBS = f"python {sys.path[0]}/dump-scheduled-jobs.py"

# ---------------------------------------------------------------------
# Ensure only documents with unique title are being preserved
# ---------------------------------------------------------------------
def prohibited_docs(cursor):
    """ Creating two sets for comparison
         - set of documents to be preserved
         - set of documents prohibited as test documents

        return True if the intersection is not empty
    """
    print("Checking for prohibited test documents")

    # Creating set of titles to be preserved
    cursor.execute("""\
     SELECT d.id, d.title
       FROM document d
       JOIN query_term t
         ON d.id = t.doc_id
       JOIN doc_type dt
         ON dt.id = d.doc_type
      WHERE t.path LIKE '%/@KeepAtRefresh'""")
    rows = cursor.fetchall()

    preserve = set()
    for _, title in rows:
        preserve.add(title)

    # Creating set of titles of prohibited documents
    cursor.execute("""\
     SELECT title, dt.name
       FROM document d
       JOIN doc_type dt
         ON d.doc_type = dt.id
      WHERE dt.name in ('Summary', 'Media', 'DrugInformationSummary',
                        'GlossaryTermConcept', 'GlossaryTermName', 'Term')
      GROUP BY title, dt.name
     HAVING COUNT(*) > 1 """)
    rows = cursor.fetchall()

    prohibited = set()
    for title, _ in rows:
        prohibited.add(title)

    if preserve & prohibited:
        print(preserve & prohibited)
        return True
    return False


# ---------------------------------------------------------------------
# Save all documents of a given type.
# ---------------------------------------------------------------------
def saveDocs(cursor, outputDir, docType):
    print(f"Saving document type {docType}")
    os.mkdir(f"{outputDir}/{docType}")
    cursor.execute("""\
    SELECT d.id, d.title, d.xml
      FROM document d
      JOIN doc_type t
        ON t.id = d.doc_type
     WHERE t.name = ?""", docType)
    row = cursor.fetchone()

    if not row:
        raise Exception(f"no documents found of type {docType}")

    while row:
        fp = open(f"{outputDir}/{docType}/{row[0]}.cdr", "w", encoding="utf-8")
        fp.write(repr(row))
        fp.close()
        row = cursor.fetchone()


# ---------------------------------------------------------------------
# Save test documents specifically marked to be restored
# ---------------------------------------------------------------------
def saveTestDocs(cursor, outputDir):
    """ For each test document to be restored include the document type,
        CDR-ID, title and XML

        Loop over each document, create a new directory for the document
        type (if it doesn't already exist) and save the document

        The restore process (PushDevDoc.py) depends on unique document
        titles.  This excludes documents like 714-X or Delirium, for which
        the English and Spanish titles are identical, to be used as
        test documents.  The process will fail if one of those documents
        is selected as a test document to be preserved.
    """

    # Check for prohibited test documents (non-unique title)
    if prohibited_docs(cursor):
        raise Exception("Refresh cannot include prohibited docs")

    print("Saving individual test documents")
    cursor.execute("""\
    SELECT dt.name, d.id, d.title, d.xml
      FROM document d
      JOIN query_term t
        ON d.id = t.doc_id
      JOIN doc_type dt
     ON dt.id = d.doc_type
     WHERE t.path LIKE '%/@KeepAtRefresh'
  ORDER BY dt.name, d.id""")
    row = cursor.fetchone()

    if not row:
        print("No test documents found to preserve")
        return

    while row:
        # For GTC documents the document title is created from the concept
        # definition and includes the CDR-ID.  The title needs to be
        # normalized in order for the restore process to find the correct
        # document.
        # Since a recent DocTitle filter change the title should already
        # be normalized but ... "belt and suspenders".
        # ----------------------------------------------------------------
        if row[0] == 'GlossaryTermConcept':
            row[2] = re.sub(r'\s+', ' ', row[2].lower().strip())

        print(f"       {row[0]} document")
        contentDir = f"{outputDir}/{row[0]}"
        Path(contentDir).mkdir(exist_ok=True)
        Path(f"{contentDir}/{int(row[1])}.cdr").write_text(repr(row[1:]),
                                                           encoding="utf-8")
        row = cursor.fetchone()


# ---------------------------------------------------------------------
# Save a table.  First line of output is the list of column names.
# Subsequent lines are the contents of each table row, one per line.
# Use Python's eval() to reconstruct the row values.
# ---------------------------------------------------------------------
def saveTable(cursor, outputDir, tableName):
    print(f"Saving table {tableName}")
    cursor.execute(f"SELECT * FROM {tableName}")
    fp = open(f"{outputDir}/tables/{tableName}", "w", encoding="utf-8")
    fp.write("%s\n" % repr([col[0] for col in cursor.description]))
    for row in cursor.fetchall():
        values = []
        for value in row:
            if isinstance(value, datetime.datetime):
                value = str(value)
            values.append(value)
        fp.write("%s\n" % repr(tuple(values)))
    fp.close()


# ---------------------------------------------------------------------
# Save the scheduled jobs in JSON and in plain text.
# ---------------------------------------------------------------------
def saveJobs(outputDir):
    print("Saving scheduled jobs")
    process = run_command(DUMP_JOBS)

    with open(f"{outputDir}/scheduled-jobs.txt", "w", encoding="utf-8") as fp:
        fp.write(process.stdout)
    process = run_command(f"{DUMP_JOBS} --json")

    with open(f"{outputDir}/scheduled-jobs.json", "w", encoding="utf-8") as fp:
        fp.write(process.stdout)


# ---------------------------------------------------------------------
# Do the work.
# ---------------------------------------------------------------------
def main():
    pull_tables = ("action",         "active_status",
                   "ctl",            "doc_type",
                   "filter_set",     "filter_set_member",
                   "format",         "grp",
                   "grp_action",     "grp_usr",
                   "link_prop_type", "link_properties",
                   "link_target",    "link_type",
                   "link_xml",       "query",
                   "query_term_def", "query_term_rule",
                   "usr")
    outputDir = time.strftime('DevData-%Y%m%d%H%M%S')
    cursor = db.connect(user="CdrGuest").cursor()
    os.makedirs("%s/tables" % outputDir)

    print(f"Saving files to {outputDir}")

    # Saving scheduled Jobs
    # ---------------------
    saveJobs(outputDir)

    for table in pull_tables:
        saveTable(cursor, outputDir, table)
    for docType in ["Filter", "PublishingSystem", "Schema"] + sys.argv[1:]:
        saveDocs(cursor, outputDir, docType)

    # Saving individual test/training documents marked for preserve
    # -------------------------------------------------------------
    saveTestDocs(cursor, outputDir)


main()
