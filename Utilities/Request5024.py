#----------------------------------------------------------------------
#
# $Id$
#
# Move misplaced OtherName elements in Term docs.
#
# BZIssue::5024
#
#----------------------------------------------------------------------
import ModifyDocs, sys, lxml.etree as etree, cdrdb

def hasMisplacedOtherNames(docId):
    try:
        cursor.execute("SELECT xml FROM document WHERE id = ?", docId)
        docXml = cursor.fetchall()[0][0]
        tree = etree.XML(docXml.encode('utf-8'))
        haveOtherNames = pastOtherNamePosition = False
        for node in tree:
            if node.tag == 'OtherName':
                if pastOtherNamePosition:
                    return True
                haveOtherNames = True
            elif type(node) is not etree._Element:
                continue
            elif node.tag in ('PreferredName', 'ReviewStatus'):
                if haveOtherNames:
                    return True
            else:
                pastOtherNamePosition = True
    except Exception, e:
        sys.stderr.write("CDR%d: %s\n" % (docId, e))
    return False

class Request5024:
    def __init__(self, docIds):
        self.docIds = docIds
    def getDocIds(self):
        return self.docIds
    def run(self, docObject):
        tree = etree.XML(docObject.xml)
        position = 0
        otherNames = []
        moveUp = []
        moveDown = []
        pastOtherNamePosition = False
        for node in tree:
            if node.tag in ("PreferredName", "ReviewStatus"):
                if otherNames:
                    moveDown += otherNames
                otherNames = []
                position += 1
            elif node.tag == "OtherName":
                if pastOtherNamePosition:
                    moveUp.append(node)
                else:
                    position += 1
                    otherNames.append(node)
            elif type(node) is etree._Element:
                pastOtherNamePosition = True
                otherNames = []
        for node in moveDown:
            # Inserting a node that already exists in the doc moves the node
            tree.insert(position, node)
        for node in moveUp:
            tree.insert(position, node)
            position += 1
        return etree.tostring(tree, pretty_print=True)

if len(sys.argv) != 4 or sys.argv[3] not in ('test', 'live'):
    sys.stderr.write("usage: %s uid pwd test|live\n" % sys.argv[0])
    sys.exit(1)
uid, pwd, flag = sys.argv[1:]
testMode = flag == 'test'
cursor = cdrdb.connect('CdrGuest').cursor()
cursor.execute("""\
SELECT DISTINCT doc_id
           FROM query_term
          WHERE path = '/Term/OtherName/OtherTermName'""")
docIds = [row[0] for row in cursor.fetchall() if hasMisplacedOtherNames(row[0])]
obj = Request5024(docIds)
job = ModifyDocs.Job(uid, pwd, obj, obj,
                     "Move misplaced OtherName elements (BZIssue::5024)",
                     validate=True, testMode=testMode)
job.run()
