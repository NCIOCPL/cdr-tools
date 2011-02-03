#----------------------------------------------------------------------
#
# $Id$
#
# Another script to fix muck-up of CT.gov import duplicates.
#
# "Records to be manually updated in the ctgov_import table:
#
# 1. CDR ID: 559148 
# current NCT ID : NCT00513227 is now obsolete.
# New NCT ID: NCT00507767 
#
# Direct all updates from NCT00507767 to CDR 559148.
# **NCT00507767 is marked as a duplicate**
#
# 2. CDR 472034 
# current NCT ID: NCT00389571 is now obsolete.
# new NCT ID: NCT00297895 
# Direct all updates from NCT00297895 to CDR 472034.
# **NCT00297895 is marked as a duplicate**
#
# 3. CDR 595388 
# current NCT ID: NCT00678223 is now obsolete.
# new NCT ID: NCT00678223 
# Direct all updates from NCT00678223  to CDR 595388 
#
#**NCT00678769 is marked as a duplicate**
#
# 4. CDR 360874
# current NCT ID: NCT00078546 is obsolete.
# new NCT ID: NCT00608257
# Direct all updates from NCT00608257 to  CDR 360874
#
# 5. CDR 558028
# current NCT ID: NCT00499772
# new NCT ID: NCT00499772
# Direct all updates from NCT00499772 to CDR 558028
#
# **NCT00488592 is marked as duplicate**
#
# 6. CDR 583208
# current NCT ID: NCT00629109 is obsolete
# new NCT ID: NCT00955019
# Direct updates from NCT00955019 to CDR 583208
#
# 7. CDR 69448
# current NCT ID: NCT00041158
# new NCT ID: NCT00037817
# Direct updates from NCT00037817 to CDR 69448
#
# **NCT00037817 is marked as a duplicate.**"
#
# BZIssue::4975
#
#----------------------------------------------------------------------
import cdrdb

conn = cdrdb.connect(dataSource='franck.nci.nih.gov') # TESTING
#conn = cdrdb.connect()
cursor = conn.cursor()
path = 'D:/cdr/Utilities/CTGovDownloads/work-20110104050005'
# Make it possible to run this more than once.
suffix = (u"; mapping fixed manually at request of WO-P "
          u"2010-12-28 by RMK [BZIssue::4975]")
for nlmId, cdrId in (('NCT00507767', 559148),
                     ('NCT00297895', 472034),
                     ('NCT00678223', 595388),
                     ('NCT00608257', 360874),
                     ('NCT00499772', 558028),
                     ('NCT00955019', 583208),
                     ('NCT00037817', 69448)):
    try:
        docXml = open("%s/%s.xml" % (path, nlmId), 'rb').read()
    except Exception, e:
        print "%s/%s.xml: %s" % (path, nlmId, e)
        continue
    cursor.execute("SELECT comment FROM ctgov_import WHERE nlm_id = ?", nlmId)
    try:
        comment = cursor.fetchall()[0][0]
        position = comment.find(suffix)
        if position != -1:
            comment = comment[:position]
    except Exception, e:
        print "%s: %s" % (nlmId, e)
        continue
    comment += suffix
    print "%s: %s" % (nlmId, comment)
    cursor.execute("""\
        UPDATE ctgov_import
           SET xml = ?,
               changed = GETDATE(),
               cdr_id = ?,
               comment = ?,
               disposition = 5
         WHERE nlm_id = ?""", (docXml, cdrId, comment, nlmId))
    print cursor.rowcount, "rows updated"
conn.commit()
