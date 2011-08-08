#----------------------------------------------------------------------
#
# $Id$
#
# Another script to clean up behind CT.gov messes.  Input has lines with
# three columns:
#  * CDR ID
#  * active NCT ID
#  * alias NCT ID
#
# Update the row for the active NCT ID, setting the disposition to Import
# Requested, with the latest XML document from NLM.  Update the row for
# the other NCT ID, marking it as Duplicate.  Reads from standard input.
#
# BZIssue::5081
#
#----------------------------------------------------------------------
import cdr, cdrdb, glob, sys

def findDownloadDirectory():
    dirs = glob.glob('d:/cdr/Utilities/CTGovDownloads/work-*')
    dirs.sort()
    return dirs[-1]

taskNumber = 5081
comment = "mapping fixed at William's request (#5081)"
conn = cdrdb.connect()
cursor = conn.cursor()
path = findDownloadDirectory()
for line in sys.stdin:
    cdrId, activeNctId, aliasNctId = line.strip().split()
    fp = open("%s/%s.xml" % (path, activeNctId), 'rb')
    docXml = fp.read()
    fp.close()
    cursor.execute("""\
        UPDATE ctgov_import
           SET xml = ?,
               changed = GETDATE(),
               dt = GETDATE(),
               cdr_id = ?,
               comment = ?,
               disposition = 5
         WHERE nlm_id = ?""", (docXml, cdrId, comment, activeNctId))
    cursor.execute("""\
        UPDATE ctgov_import
           SET disposition = 4
         WHERE nlm_id = ?""", aliasNctId)
conn.commit()
