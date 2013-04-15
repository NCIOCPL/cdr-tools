#----------------------------------------------------------------------
#
# $Id$
#
# Global change to drop NLM site information from CTGovProtocol
# documents which also have site information from CTRP.
#
# BZIssue::5292
#
#----------------------------------------------------------------------
import sys, lxml.etree as etree, ModifyDocs, cdrdb

class SiteDropper:
    def getDocIds(self):
        cursor = cdrdb.connect("CdrGuest").cursor()
        cursor.execute("""\
SELECT DISTINCT nlm.doc_id
           FROM query_term nlm
           JOIN query_term ctrp
             ON ctrp.doc_id = nlm.doc_id
          WHERE nlm.path LIKE '/CTGovProtocol/Location%'
            AND ctrp.path =  '/CTGovProtocol/CTRPInfo/CTRPLocation' +
                             '/CTRPFacility/PDQOrganization/@cdr:ref'
       ORDER BY nlm.doc_id""")
        return [row[0] for row in cursor.fetchall()]
    def run(self, docObject):
        try:
            tree = etree.XML(docObject.xml)
            for location in tree.findall("Location"):
                tree.remove(location)
            newXml = etree.tostring(tree, xml_declaration=True,
                                    encoding="utf-8")
            #save(newXml, "new", docObject.id)
            #save(docObject.xml, "old", docObject.id)
            return newXml
        except Exception, e:
            self.job.log("%s: %s" % (docObject.id, e))
            return docObject.xml

def save(xml, prefix, id):
    fp = open("d:/tmp/bz5292/%s-%s.xml" % (id, prefix), "wb")
    fp.write(xml)
    fp.close()

if __name__ == "__main__":
    if len(sys.argv) != 4 or sys.argv[3] not in ("live", "test"):
        sys.stderr.write("usage: %s uid pwd live|test\n" % sys.argv[0])
        sys.exit(1)
    uid, pwd, mode = sys.argv[1:]
    testMode = mode == "test"
    obj = SiteDropper()
    job = ModifyDocs.Job(uid, pwd, obj, obj,
                         "Drop NLM site info (BZIssue::5292)",
                         validate=True, testMode=testMode)
    obj.job = job
    job.run()
