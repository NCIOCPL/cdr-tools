#----------------------------------------------------------------------
#
# $Id$
#
# Global change to remove placeholders inadvertently added to new
# CT.gov protocol documents.
#
# Preparation for this job involved creating the xctrp_info_placeholder
# table on Bach to hold the CDR IDs for the documents needing the
# modification.
3
#----------------------------------------------------------------------
import sys, cdrdb, ModifyDocs

# Object to identify documents and fix them.
class Transform:
    def getDocIds(self):
        cursor = cdrdb.connect("CdrGuest").cursor()
        cursor.execute("SELECT id FROM xctrp_info_placeholder2")
        return [row[0] for row in cursor.fetchall()]

    def run(self, docObj):
        return docObj.xml.replace("@@CTRPInfo@@", "")

# Collect command-line arguments.
if len(sys.argv) < 4 or sys.argv[3].lower() not in ("test", "live"):
    print("usage: RemoveCtrpInfoPlaceholders.py uid pw {test|live}")
    sys.exit(1)
uid  = sys.argv[1]
pw   = sys.argv[2]
test = sys.argv[3].lower() != "live"

# Create the objects.
obj  = Transform()
cmnt = "Remove @@CTRPInfo@@ placeholders added to new CTGovProtocol docs"
job  = ModifyDocs.Job(uid, pw, obj, obj, cmnt, validate=True, testMode=test)

# Run the job.
job.run()
