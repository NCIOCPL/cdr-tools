#----------------------------------------------------------------------
#
# $Id$
#
# Script to fix muck-up of CT.gov import duplicate.
#
# BZIssue::4857
#
#----------------------------------------------------------------------
import cdrdb

#conn = cdrdb.connect(dataSource='mahler.nci.nih.gov') TESTING
conn = cdrdb.connect()
cursor = conn.cursor()
path = 'd:/cdr/Utilities/CTGovDownloads/work-20100602050005/NCT00319748.xml'
docXml = open(path, 'rb').read()
cursor.execute("SELECT comment FROM ctgov_import WHERE nlm_id = 'NCT00319748'")
comment = cursor.fetchall()[0][0]
# Make it possible to run this more than once.
suffix = (u"; fixed manually at request of WO-P "
          u"2010-06-02 by RMK [BZIssue::4857]")
position = comment.find(suffix)
if position != -1:
    comment = comment[:position]
comment += suffix
print "COMMENT: %s" % comment
cursor.execute("""\
    UPDATE ctgov_import
       SET xml = ?,
           changed = GETDATE(),
           cdr_id = 484380,
           comment = ?,
           disposition = 5
     WHERE nlm_id = 'NCT00319748'""", (docXml, comment))
conn.commit()
