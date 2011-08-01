#----------------------------------------------------------------------
#
# $Id: $
#
# Two more trials to be surgically fixed for William.
#
# BZIssue::5021
#
#----------------------------------------------------------------------
import cdr, cdrdb, glob, sys

path = "d:/cdr/Utilities/CTGovDownloads/work-20110418050004"
conn = cdrdb.connect()
cursor = conn.cursor()
comment = (u"mapping fixed manually at request of WO-P "
           u"2011-04-18 by RMK [BZIssue::5021]")
for cdrId, nctInactive, nctActive in ((674892, "NCT01143415", "NCT01195415"),
                                      (583228, "NCT00631930", "NCT00600353")):
    sys.stdout.write("SWITCHING CDR%d FROM %s TO %s\n" %
                     (cdrId, nctInactive, nctActive))
    try:
        fp = open("%s/%s.xml" % (path, nctActive), 'rb')
    except:
        sys.stdout.write("FAILURE: NOT IN LATEST DOWNLOAD SET\n")
        continue
    docXml = fp.read()
    fp.close()
    cursor.execute("""\
UPDATE ctgov_import
   SET dt = GETDATE(),
       comment = ?,
       disposition = 4
 WHERE nlm_id = ?""", (comment, nctInactive))
    cursor.execute("""\
UPDATE ctgov_import
   SET dt = GETDATE(),
       comment = ?,
       disposition = 5,
       xml = ?,
       changed = GETDATE()
 WHERE nlm_id = ?""", (comment, unicode(docXml, 'utf-8'), nctActive))
conn.commit()
