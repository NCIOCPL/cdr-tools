#----------------------------------------------------------------------
#
# $Id: Request4857.py 9649 2010-06-02 19:21:34Z bkline $
#
# Another script to fix muck-up of CT.gov import duplicates.
#
# "The first two trials did not convert as expected when the transfer
# blocks were added to them. Please update the ctgov_import table so
# that they are converted into CTGovProtocol documents.
#
# 1.    InScope =  CDR0000539474  NCT00385398 
#              (CTGov = 515053 NCT00385398)
#
# 2.    InScope = CDR0000540298 NCT00161187
#          (CTGov = 449716 NCT00161187)
#
#          ------------------------------------------------
#
# The following trials have duplicate ctgov trials which will be deleted
# eventually. We will want all potential ctgov updates to go to the
# non-duplicate trials.
#
# 1. ctgov: 542753 NCT00454324
#    ctgov (duplicate): 698192 NCT00454324
#
#    Please direct all updates to 542753
#
# 2. ctgov: 485432  NCT00323063 
#    ctgov (duplicate) : 688997 NCT00323063 
#
#   Please direct all updates to 485432"
#
# BZIssue::4953
#
#----------------------------------------------------------------------
import cdrdb

# conn = cdrdb.connect(dataSource='franck.nci.nih.gov') # TESTING
conn = cdrdb.connect()
cursor = conn.cursor()
path = 'D:/cdr/Utilities/CTGovDownloads/work-20101116050004'
# Make it possible to run this more than once.
suffix = (u"; mapping fixed manually at request of WO-P "
          u"2010-11-16 by RMK [BZIssue::4953]")
for nlmId, cdrId in (('NCT00385398', 539474),
                     ('NCT00161187', 540298),
                     ('NCT00454324', 542753),
                     ('NCT00323063', 485432)):
    docXml = open("%s/%s.xml" % (path, nlmId), 'rb').read()
    cursor.execute("SELECT comment FROM ctgov_import WHERE nlm_id = ?", nlmId)
    comment = cursor.fetchall()[0][0]
    position = comment.find(suffix)
    if position != -1:
        comment = comment[:position]
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
