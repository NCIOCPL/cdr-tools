#----------------------------------------------------------------------
#
# $Id$
#
# Script to manually adjust ctgov_import table for Clinical Center trials
# with duplicate CT.gov records.
#
# BZIssue::4871
#
#----------------------------------------------------------------------
import cdrdb, ExcelReader, re

pattern = re.compile("ctgov record (\\d+) needs to be un-blocked")
conn = cdrdb.connect(dataSource='mahler.nci.nih.gov')
# conn = cdrdb.connect()
cursor = conn.cursor()
docDir = 'd:/cdr/Utilities/CTGovDownloads/work-20100701050003'
book = ExcelReader.Workbook('d:/tmp/Request4871.xls')
sheet = book[0]
for row in sheet:
    if row[0].val == 'Protocol Number':
        continue
    nlmId = row[1].val
    comment = row[4].val
    match = pattern.match(comment)
    if match:
        docType = 'CTGovProtocol'
        cdrId = int(match.group(1))
    else:
        docType = 'InScopeProtocol'
        cdrId = int(str(row[3].val).split('/')[0].split('.')[0])
    try:
        fp = open("%s/%s.xml" % (docDir, nlmId), "rb")
        doc = fp.read()
        fp.close()
        print "importing %s (%d bytes) as %s doc CDR%d" % (nlmId, len(doc),
                                                           docType, cdrId)
    except:
        print "nothing to import for %s into %s doc CDR%d" % (nlmId, docType,
                                                              cdrId)
        
## docXml = open(path, 'rb').read()
## cursor.execute("SELECT comment FROM ctgov_import WHERE nlm_id = 'NCT00319748'")
## comment = cursor.fetchall()[0][0]
## # Make it possible to run this more than once.
## suffix = (u"; fixed manually at request of WO-P "
##           u"2010-06-02 by RMK [BZIssue::4857]")
## position = comment.find(suffix)
## if position != -1:
##     comment = comment[:position]
## comment += suffix
## print "COMMENT: %s" % comment
## cursor.execute("""\
##     UPDATE ctgov_import
##        SET xml = ?,
##            changed = GETDATE(),
##            cdr_id = 484380,
##            comment = ?,
##            disposition = 5
##      WHERE nlm_id = 'NCT00319748'""", (docXml, comment))
## conn.commit()
