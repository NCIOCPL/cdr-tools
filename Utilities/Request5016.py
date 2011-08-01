#----------------------------------------------------------------------
#
# $Id$
#
# Move misplaced Comment elements in Term docs.
#
# BZIssue::5016
#
#----------------------------------------------------------------------
import ModifyDocs, sys, lxml.etree as etree, cdrdb

def hasMisplacedComments(docId):
    try:
        cursor.execute("SELECT xml FROM document WHERE id = ?", docId)
        docXml = cursor.fetchall()[0][0]
        tree = etree.XML(docXml.encode('utf-8'))
        comments = bottom = False
        for node in tree:
            # No other elements should appear below these two.
            if node.tag in ("PdqKey", "DateLastModified"):
                bottom = True

                # Comments we've seen so far are in the right place.
                comments = False
            else:
                if node.tag == "Comment":
                    if bottom:
                        # Comment found below PdqKey or DateLastModified.
                        return True
                    else:
                        comments = True
                elif comments and type(node) is etree._Element:
                    # Comment found too high in document.
                    return True
    except Exception, e:
        sys.stderr.write("CDR%d: %s\n" % (docId, e))
    return False

class Request5016:
    def __init__(self, docIds):
        self.docIds = docIds
    def getDocIds(self):
        return self.docIds
    def run(self, docObject):
        tree = etree.XML(docObject.xml)
        position = 0
        comments = []
        moveUp = []
        moveDown = []
        bottom = False
        for node in tree:
            if node.tag in ("PdqKey", "DateLastModified"):
                bottom = True
            else:
                if bottom:
                    if node.tag == "Comment":
                        moveUp.append(node)
                else:
                    position += 1
                    if node.tag == "Comment":
                        comments.append(node)
                    elif comments and type(node) is etree._Element:
                        moveDown += comments
                        comments = []
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
SELECT d.id
  FROM document d
  JOIN doc_type t
    ON t.id = d.doc_type
 WHERE t.name = 'Term'""")
docIds = [row[0] for row in cursor.fetchall() if hasMisplacedComments(row[0])]
obj = Request5016(docIds)
job = ModifyDocs.Job(uid, pwd, obj, obj,
                     "Move misplaced Comment elements (BZIssue::5016)",
                     validate=True, testMode=testMode)
job.run()
