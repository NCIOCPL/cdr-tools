#----------------------------------------------------------------------
# $Id$
# JIRA::OCECDR-3606
#----------------------------------------------------------------------
import sys
import xlrd
import glob
import os
import re

TABLE = "glossary_term_audio_request"
DEFAULT_DIR = "../Report/SpreadsheetsForVanessa"

docs = {}
directory = len(sys.argv) > 1 and sys.argv[1] or DEFAULT_DIR
for path in glob.glob("%s/Report4926-*.xls" % directory):
    name = os.path.basename(path)
    match = re.search(r"Report4926-(\d\d\d\d)(\d\d)(\d\d)\.xls", name, re.I)
    if match:
        date = "%s-%s-%s" % (match.group(1), match.group(2), match.group(3))
    else:
        raise Exception("unexpected filename format: %s" % name)
    book = xlrd.open_workbook(path)
    sheet = book.sheet_by_index(0)
    for row in range(sheet.nrows):
        try:
            value = sheet.row(row)[0].value
            doc_id = int(value)
            if doc_id not in docs:
                docs[doc_id] = (name, date)
        except:
            #print "skipped %s" % repr(value)
            pass
for doc_id in sorted(docs.keys()):
    name, date = docs[doc_id]
    print "INSERT INTO %s VALUES (%d, '%s', '%s')" % (TABLE, doc_id, name, date)
