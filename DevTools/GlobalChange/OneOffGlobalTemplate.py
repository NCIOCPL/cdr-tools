#----------------------------------------------------------------------
#
# Skeletal template for one-off global change jobs using the lxml.etree
# parser to perform the document modifications.
#
#----------------------------------------------------------------------
import ModifyDocs, sys, lxml.etree as etree

class OneOffGlobal:
    def __init__(self, docIds=None):
        self.job = None
        self.docIds = docIds

    def getDocIds(self):
        return self.docIds

    def run(self, docObject):
        tree = etree.XML(docObject.xml)
        for node in tree.findall('foo'):
            etree.SubElement(node, 'bar').text = u'foobar'
        return etree.tostring(tree)

if __name__ == "__main__":

    if len(sys.argv) != 4 or sys.argv[3] not in ('test', 'live'):
        sys.stderr.write("usage: %s uid pwd test|live\n" % sys.argv[0])
        sys.exit(1)
    uid, pwd, flag = sys.argv[1:]
    testMode = flag == 'test'

    # Replace or delete sample docIds
    obj = OneOffGlobal((444444, 555555, 666666))

    # Replace comment
    job = ModifyDocs.Job(uid, pwd, obj, obj,
                         "Add bar children to all foos.  BZIssue::1234",
                         validate=True, testMode=testMode)

    # Add reference to job back into the global change object
    # Allows access to logging in the ModifyDocs log via self.job.log()
    obj.job = job

    # Uncomment to see one doc transformation for debugging
    # job.setMaxDocs(1)

    job.run()
