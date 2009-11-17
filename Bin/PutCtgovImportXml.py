#----------------------------------------------------------------------
#
# $Id$
#
# Tool to replace the xml column from the ctgov_import table for a given
# trial.
#
#----------------------------------------------------------------------
import cdrdb, sys

if len(sys.argv) != 3:
    sys.stderr.write("usage: PutCtgovImportXml.py NCT-ID XML-FILENAME\n")
    sys.exit(2)
nctId = sys.argv[1]
name = sys.argv[2]
fp = open(name)
docXml = fp.read()
fp.close()
conn = cdrdb.connect()
cursor = conn.cursor()
cursor.execute("UPDATE ctgov_import SET xml = ? WHERE nlm_id = ?", (docXml,
                                                                    nctId))
if cursor.rowcount != 1:
    sys.stderr.write("unable to find row for '%s'\n" % nctId)
else:
    print "updated xml for '%s'\n" % nctId
conn.commit()
