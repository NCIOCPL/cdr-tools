#----------------------------------------------------------------------
#
# $Id$
#
# Programmatically strip Board Membership information out of Person documents.
#
# BZIssue::1045
#
#----------------------------------------------------------------------
import cdr, cdrdb, sys, ModifyDocs

#----------------------------------------------------------------------
# The Filter class is given to the ModifyDocs.Job object, which invokes
# the getDocIds() method to retrieve a list of CDR document IDs for
# processing.
#----------------------------------------------------------------------
class Filter:
    def getDocIds(self):
        conn = cdrdb.connect('CdrGuest')
        cursor = conn.cursor()
        cursor.execute("""\
    SELECT DISTINCT doc_id
               FROM query_term
              WHERE path LIKE '/Person/ProfessionalInformation' +
                              '/PDQBoardMembershipDetails%'
           ORDER BY doc_id""")
        return [row[0] for row in cursor.fetchall()]

#----------------------------------------------------------------------
# The Transform class is given to the ModifyDocs.Job object, which in
# turn gives it to each ModifyDocs.Doc object.  The run() method of
# this class takes a cdr.Doc object and returns a (possibly) modified
# copy of that object's xml member.
#
# See comment at top for this job's logic.
#----------------------------------------------------------------------
class Transform:
    def run(self, docObj):
        filter = ['name:Strip PDQBoardMembershipDetails']
        result = cdr.filterDoc('guest', filter, doc = docObj.xml)
        if type(result) in (type(""), type(u"")):
            sys.stderr.write("%s: %s\n" % (docObj.id, result))
            return docObj.xml
        return result[0]

if len(sys.argv) < 3:
    sys.stderr.write("usage: %s uid pwd [LIVE]\n" % sys.argv[0])
    sys.exit(1)
testMode = len(sys.argv) < 4 or sys.argv[3] != "LIVE"
job = ModifyDocs.Job(sys.argv[1], sys.argv[2], Filter(), Transform(),
                     "Strip PDQ Board Membership Details (request #1045).",
                     testMode = testMode)
job.run()
