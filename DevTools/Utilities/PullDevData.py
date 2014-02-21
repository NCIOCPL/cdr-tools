#----------------------------------------------------------------------
#
# $Id$
#
# Pulls control documents and tables which need to be preserved from the
# development server in preparation for refreshing the CDR database from
# the production server.  If the development server has any document
# types which don't exist at all and for which documents exist which need
# to be preserved, name those document types on the command line.
#
# Usage:
#   SaveDevDocs.py [newdoctype [newdoctype ...] ]
#
#----------------------------------------------------------------------
import cdrdb, os, sys, time

#----------------------------------------------------------------------
# Save all documents of a given type.
#----------------------------------------------------------------------
def saveDocs(cursor, outputDir, docType):
    print "Saving %s documents" % docType
    os.mkdir("%s/%s" % (outputDir, docType))
    cursor.execute("""\
SELECT d.id, d.title, d.xml
  FROM document d
  JOIN doc_type t
    ON t.id = d.doc_type
 WHERE t.name = ?""", docType)
    row = cursor.fetchone()
    if not row:
        raise Exception("no documents found of type %s" % docType)
    while row:
        fp = open("%s/%s/%d.cdr" % (outputDir, docType, row[0]), "w")
        fp.write(repr(row))
        fp.close()
        row = cursor.fetchone()

#----------------------------------------------------------------------
# Save a table.  First line of output is the list of column names.
# Subsequent lines are the contents of each table row, one per line.
# Use Python's eval() to reconstruct the row values.
#----------------------------------------------------------------------
def saveTable(cursor, outputDir, tableName):
    print "Saving %s table" % tableName
    cursor.execute("SELECT * FROM %s" % tableName)
    fp = open("%s/%s.table" % (outputDir, tableName), "w")
    fp.write("%s\n" % repr([col[0] for col in cursor.description]))
    for row in cursor.fetchall():
        fp.write("%s\n" % repr(row))
    fp.close()

#----------------------------------------------------------------------
# Do the work.
#----------------------------------------------------------------------
def main():
    outputDir = time.strftime('DevFiles-%Y%m%d%H%M%S')
    cursor = cdrdb.connect("CdrGuest").cursor()
    os.mkdir(outputDir)
    print "Saving files to %s" % outputDir
    for table in ("doc_type", "filter_set", "filter_set_member",
                  "query_term_def", "link_type", "link_xml", "link_target",
                  "link_prop_type", "link_properties"):
        saveTable(cursor, outputDir, table)
    for docType in ["Filter", "PublishingSystem", "Schema"] + sys.argv[1:]:
        saveDocs(cursor, outputDir, docType)

main()
