#----------------------------------------------------------------------
#
# $Id$
#
# Bug #1034 implemented an alphabetical sort of the protocolsites when
# the document is saved. However there are several documents that have
# not been resaved since that time and these lead to "noise" in the diff
# reports for Electronic mailer updates. The server enhancement was
# moved to BACH on March 5.  To be on the safe side, we should look for
# protocols that have a status of Active, Approved-not yet active, and
# Temporarily closed and have not had a new version or a cwd saved since
# March 4 2004. It is our understanding that the one- off program will
# check these documents out and resave following the logic for
# versioning that has been established. We would like this to be tested
# on Mahler and moved to BACH before we implement the emailers on BACH.
#
# BZIssue::1316
#
#----------------------------------------------------------------------
import cdr, cdrdb, ModifyDocs, sys

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
    CREATE TABLE #t (id INTEGER, status VARCHAR(80), dt DATETIME)""")
        conn.commit()
        cursor.execute("""\
     INSERT INTO #t (id, status, dt)
 SELECT DISTINCT s.doc_id, s.value, MAX(a.dt)
            FROM query_term s
            JOIN audit_trail a
              ON a.document = s.doc_id
           WHERE s.path = '/InScopeProtocol/ProtocolAdminInfo'
                        + '/CurrentProtocolStatus'
        GROUP BY s.doc_id, s.value""", timeout = 300)
        conn.commit()
        cursor.execute("""\
 SELECT DISTINCT id
            FROM #t
           WHERE dt < '2004-03-05'
             AND status IN ('Active',
                            'Approved-not yet active',
                            'Temporarily closed')
         ORDER BY id""")
        return [row[0] for row in cursor.fetchall()]

#----------------------------------------------------------------------
# The Transform class is given to the ModifyDocs.Job object, which in
# turn gives it to each ModifyDocs.Doc object.  The run() method of
# this class takes a cdr.Doc object and returns a (possibly) modified
# copy of that object's xml member.
#
# For this job, we append a comment to force re-saving the document.
#----------------------------------------------------------------------
class Transform:
    def run(self, docObj):
        return docObj.xml + "\n<!-- Protocol sites sorted -->\n"

job = ModifyDocs.Job(sys.argv[1], sys.argv[2], Filter(), Transform(),
                     "Force ordering of protocol sites (request #1316).")
job.run()
