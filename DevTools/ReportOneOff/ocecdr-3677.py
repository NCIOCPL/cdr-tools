#----------------------------------------------------------------------
#
# $Id$
#
# Fetch CTRP document from ctrp_import table.
#
#----------------------------------------------------------------------
import cdrdb, sys

if len(sys.argv) != 2:
    sys.stderr.write("usage: ocecdr-3677.py ctrp-id > ctrp-id.xml\n")
    sys.exit(1)
cursor = cdrdb.connect("CdrGuest").cursor()
cursor.execute("""\
SELECT doc_xml
  FROM ctrp_import
 WHERE ctrp_id = ?""", sys.argv[1])
print cursor.fetchall()[0][0].encode("utf-8")
