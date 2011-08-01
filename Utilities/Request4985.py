#----------------------------------------------------------------------
#
# $Id$
#
# Global change to populate new GovernmentEmployee element in
# PDQBoardMemberInfo documents.  Job is driven by data in Robin's
# Excel spreadsheet, which contains the CDR document ID in column
# A and the a status value in column D.  The unique status values
# are:
#     * Y
#     * Y - Retired
#     * He is being removed from the Board
#     * N
#
# BZIssue::4985
#
#----------------------------------------------------------------------
import sys, cdr, ExcelReader, ModifyDocs, lxml.etree as etree

class Request4985:
    def __init__(self, statuses):
        self.statuses = statuses
    def getDocIds(self):
        docIds = self.statuses.keys()
        docIds.sort()
        return docIds
    def run(self, docObject):
        docId = cdr.exNormalize(docObject.id)[1]
        status = statuses[docId]
        tree = etree.XML(docObject.xml)
        if tree.findall('GovernmentEmployee'):
            return docObject.xml
        position = 0
        for child in tree:
            if child.tag in ('BoardMemberName', 'BoardMemberContact',
                             'BoardMemberContactMode', 'Affiliations'):
                position += 1
        child = etree.Element('GovernmentEmployee')
        employee = 'No'
        honorariaDeclined = None
        if status == 'Y':
            employee = 'Yes'
        elif status == 'Y - Retired':
            honorariaDeclined = 'Yes'
        elif status != 'N':
            employee = 'Unknown'
        child.text = employee
        if honorariaDeclined:
            child.set('HonorariaDeclined', honorariaDeclined)
        tree.insert(position, child)
        return etree.tostring(tree)

book = ExcelReader.Workbook(r'\\franck\d$\tmp'
                            r'\BoardMemberGovtEmployeeStatus.xls')
sheet = book[0]
statuses = {}
for row in sheet:
    try:
        docId = int(row[0].val)
        status = row[3].val
        statuses[docId] = status
    except Exception, e:
        print e
if len(sys.argv) != 4 or sys.argv[3] not in ('test', 'live'):
    sys.stderr.write("usage: %s uid pwd test|live\n" % sys.argv[0])
    sys.exit(1)
uid, pwd, flag = sys.argv[1:]
testMode = flag == 'test'
obj = Request4985(statuses)
job = ModifyDocs.Job(uid, pwd, obj, obj, "Request 4985",
                     validate=True, testMode=testMode)
job.run()
