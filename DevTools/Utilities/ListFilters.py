#----------------------------------------------------------------------
#
# $Id$
#
# Command-line script to list filters by name with file names based
# on Bach CDR IDs.  Useful for finding a CDR filter in a Subversion
# sandbox.
#
#----------------------------------------------------------------------
import cdrdb, cdr

cursor = cdrdb.connect('CdrGuest').cursor()
cursor.execute("""\
    SELECT d.id, d.title
      FROM document d
      JOIN doc_type t
        ON t.id = d.doc_type
     WHERE t.name = 'filter'
  ORDER BY d.title""")
for docId, docTitle in cursor.fetchall():
    print "CDR%010d.xml %s" % (docId, docTitle.encode('utf-8'))
