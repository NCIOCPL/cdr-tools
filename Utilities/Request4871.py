#----------------------------------------------------------------------
#
# $Id$
#
# [Comment #22 in issue 4871 from William]
#
# It looks like we may have to look further into this before going forward
# because there is an issue with at least 2 of the trials we tested (482415
# and 485379). 
#
# For 482415, the NCT ID in the inscope document is NCT00337311 and when it
# converted, the ctgov protocol rightly had the same NCT ID of NCT00337311.
# However, NCT00337311 is marked as the obsolete NCT ID on clinicaltrials.gov,
#
# http://www.clinicaltrials.gov/ct2/show/NCT00321555?term=NCT00337311&rank=1
#
# (which may mean that we will not receive any updates to the trial) and it
# looks like because of that about July 06, a trial with the active NCT ID
# of the trial showed up on the ctgov review page  ( we have not imported
# or marked as a duplicate yet) l, which is - NCT00321555.
#
# The second trial - CDR485379 may eventually end up with the same issue (of
# receiving another trial in the review page with the active NCT ID) because
# the active NCT ID on clinicaltrials.gov is not what is currently in the
# converted ctgov document. NCT00343772 is what is in the converted ctgov
# document and NCT00326495 is the active NCT ID on clinicaltrials.gov with
# NCT00343772 marked as obsolete.
#
# Bob, do you have any suggestions of how to deal with the ones we have
# already converted (above)?
#
# [Response from Bob]
#
# You want CDR485379 to be updated from NCT00326495 and CDR482415 to be
# updated from NCT00321555, right?  If so, what would you say to having me
# manually set the cdr_id, title, xml, downloaded, changed, phase, and
# disposition columns for the two rows in ctgov_import for those NCT IDs,
# and mark the rows for NCT00343772 and NCT00337311 with disposition of
# duplicate, and then run an import job?
#
# [Response from William]
#
# I believe this will solve the problem.
#
# BZIssue::4871
#
#----------------------------------------------------------------------
import cdrdb, sys, lxml.etree as etree

DISPOSITION_DUPLICATE = 4
DISPOSITION_IMPORT    = 5
COMMENT               = "INFORMATION ADDED MANUALLY FOR CIAT: REQUEST 4871"

class ProblemChild:
    @staticmethod
    def haveRow(cursor, nctId):
        cursor.execute("SELECT COUNT(*) FROM ctgov_import where nlm_id = ?",
                       nctId)
        return cursor.fetchall()[0][0] == 1
    def __init__(self, pdqNctId, ccNctId, cdrId, directory, cursor):
        self.pdqNctId = pdqNctId
        self.ccNctId  = ccNctId
        self.cdrId    = int(cdrId)
        self.docXml   = open("%s/%s.xml" % (directory, ccNctId)).read()
        self.title    = None
        self.phase    = None
        self.verified = None
        self.changed  = None
        self.havePdq  = ProblemChild.haveRow(cursor, self.pdqNctId)
        self.haveCc   = ProblemChild.haveRow(cursor, self.ccNctId)
        tree = etree.XML(self.docXml)
        for node in tree.findall('official_title'):
            self.title = node.text
        for node in tree.findall('lastchanged_date'):
            self.changed = node.text
        for node in tree.findall('verification_date'):
            self.verified = node.text
        self.phase = ";".join([p.text for p in tree.findall('phase')])
    def fix(self, conn, cursor, downloaded):
        if self.haveCc:
            cursor.execute("""\
                UPDATE ctgov_import
                   SET xml = ?,
                       title = ?,
                       phase = ?,
                       cdr_id = ?,
                       downloaded = ?,
                       dt = GETDATE(),
                       changed = ?,
                       verified = ?,
                       comment = ?,
                       disposition = ?
                 WHERE nlm_id = ?""", (self.docXml, self.title, self.phase,
                                       self.cdrId, downloaded, self.changed,
                                       self.verified, COMMENT,
                                       DISPOSITION_IMPORT, self.ccNctId))
        else:
            cursor.execute("""\
                INSERT INTO ctgov_import (nlm_id, xml, title, phase, 
                                          downloaded, disposition, dt,
                                          verified, changed, cdr_id,
                                          comment)
                     VALUES (?, ?, ?, ?, ?, ?, GETDATE(), ?, ?, ?, ?)
                     """, (self.ccNctId, self.docXml, self.title, self.phase,
                           downloaded, DISPOSITION_IMPORT, self.verified,
                           self.changed, self.cdrId, COMMENT))
        if self.havePdq:
            cursor.execute("""\
                UPDATE ctgov_import
                   SET cdr_id = ?,
                       dt = GETDATE(),
                       disposition = ?,
                       comment = ?
                 WHERE nlm_id = ?""", (self.cdrId, DISPOSITION_DUPLICATE,
                                       COMMENT, self.pdqNctId))
        else:
            cursor.execute("""\
                INSERT INTO ctgov_import (nlm_id, disposition, cdr_id, dt,
                                          comment)
                     VALUES (?, ?, ?, GETDATE(), ?)""", (self.pdqNctId,
                                                         DISPOSITION_DUPLICATE,
                                                         self.cdrId,
                                                         COMMENT))
        conn.commit()

if len(sys.argv) != 4:
    sys.stderr.write("""\
usage: Request4871Fix.py download-directory download-date id-file
 e.g.: Request4871Fix.py d:work-20100713050004 2010-07-13 trial-ids.txt

Format of ID file must have three IDs for one trial on each line, separated
by whitespace:
  NCT ID for PDQ's InScopeProtocol
  NCT ID for Clinical Center's protocol
  CDR ID for PDQ's InScopeProtocol

These rows can be copied and pasted from the spreadsheet for Issue 4871
posted by CIAT with the initial comment

For example:
NCT00343772\tNCT00326495\t485379
NCT00337311\tNCT00321555\t482415
NCT00331617\tNCT00304460\t473925
NCT00313664\tNCT00302159\t473181
NCT00304057\tNCT00273910\t465410
""")
    sys.exit(1)
directory, date, idFileName = sys.argv[1:]
conn = cdrdb.connect()
cursor = conn.cursor()
idFile = open(idFileName)
for row in idFile:
    pdqNctId, ccNctId, cdrId = row.split()
    trial = ProblemChild(pdqNctId, ccNctId, cdrId, directory, cursor)
    print "marking %s for import as CDR%d" % (trial.ccNctId, trial.cdrId)
    trial.fix(conn, cursor, date)
