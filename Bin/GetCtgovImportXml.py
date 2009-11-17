#----------------------------------------------------------------------
#
# $Id$
#
# Tool to get the xml column from the ctgov_import table for a given
# trial and print it to standard output.
#
#----------------------------------------------------------------------
import cdrdb, sys

if len(sys.argv) != 2:
    sys.stderr.write("usage: GetCtgovImportXml.py NCT-ID\n")
    sys.exit(2)
nctId = sys.argv[1]
cursor = cdrdb.connect('CdrGuest').cursor()
cursor.execute("SELECT xml FROM ctgov_import WHERE nlm_id = ?", nctId)
rows = cursor.fetchall()
if not rows:
    sys.stderr.write("unable to find trial with ID '%s'\n" % nctId)
    sys.exit(3)
print rows[0][0].encode('utf-8')
