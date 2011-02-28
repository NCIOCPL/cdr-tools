#----------------------------------------------------------------------
#
# $Id$
#
# Skeletal template for one-off global change jobs using the lxml.etree
# parser to perform the document modifications.
#
#----------------------------------------------------------------------
import ModifyDocs, sys, lxml.etree as etree

class OneOffGlobal:
    def __init__(self, docIds):
        self.docIds = docIds
    def getDocIds(self):
        return self.docIds
    def run(self, docObject):
        for node in etree.XML(docObject.xml).findall('foo'):
            etree.SubElement(node, 'bar').text = u'foobar'
        return etree.tostring(tree)

if len(sys.argv) != 4 or sys.argv[3] not in ('test', 'live'):
    sys.stderr.write("usage: %s uid pwd test|live\n" % sys.argv[0])
    sys.exit(1)
uid, pwd, flag = sys.argv[1:]
testMode = flag == 'test'
obj = OneOffGlobal((444444, 555555, 666666))
job = ModifyDocs.Job(uid, pwd, obj, obj, "Add bar children to all foos",
                     validate=True, testMode=testMode)
job.run()
