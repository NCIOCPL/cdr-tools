#!/usr/bin/env python
#----------------------------------------------------------------------
#
# Pulls documents which need to be preserved (identified by the attribute
# @KeepAtRefresh) from the QA server in preparation for refreshing the CDR 
# database from the production server.  If the development server has any 
# document types which don't exist at all and for which documents exist 
# which need # to be preserved, name those document types on the command 
# line.
#
# Usage:
#   PullDevData.py [newdoctype [newdoctype ...] ]
#
#----------------------------------------------------------------------

import os
import re
import sys
import time
from cdrapi import db
from pathlib import Path

#----------------------------------------------------------------------
# Ensure only documents with unique title are being preserved
#----------------------------------------------------------------------
def prohibited_docs(cursor):
    """ Creating two sets for comparison
         - set of documents to be preserved
         - set of documents prohibited as test documents

        return True if the intersection is not empty
    """
    print(f"Checking for prohibited test documents")

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


#----------------------------------------------------------------------
# Save test documents specifically marked to be restored
#----------------------------------------------------------------------
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
            row[2] = re.sub(r'\s+',' ', row[2].lower().strip())

        print(f"       {row[0]} document")
        contentDir = f"{outputDir}/{row[0]}"
        Path(contentDir).mkdir(exist_ok=True)
        Path(f"{contentDir}/{int(row[1])}.cdr").write_text(repr(row[1:]),
                                                           encoding="utf-8")
        row = cursor.fetchone()

#----------------------------------------------------------------------
# Do the work.
#----------------------------------------------------------------------
def main():
    outputDir = time.strftime('DevData-%Y%m%d%H%M%S')
    cursor = db.connect(user="CdrGuest").cursor()
    os.mkdir(f"{outputDir}")

    print(f"Saving files to {outputDir}")

    # Saving individual test/training documents marked for preserve
    # -------------------------------------------------------------
    saveTestDocs(cursor, outputDir)

main()
