#----------------------------------------------------------------------
#
# $Id: Request1846.py,v 1.1 2005-10-13 22:49:10 ameyer Exp $
#
# One off program to create publishable versions from CTGovImport'ed
# documents for which the last version is not publishable.
#
# We will log the results of this run in a similar fashion to other
# one-off global change requests.  However, because thiiltering of
# the documents, we don't use the ModifyDocs class.
#
# $Log: not supported by cvs2svn $
#
#----------------------------------------------------------------------

import sys, time, cdr, cdrdb

#----------------------------------------------------------------------
# Log a message
#----------------------------------------------------------------------
LOGFILE = "d:/cdr/log/Request1846.log"
lf      = None

def log(msg):
    """
    Write message to screen and program specific logfile,
    using ModifyDocs.py format.

    Pass:
        Message
    """
    global LOGFILE, lf
    if not lf:
        lf = open(LOGFILE, "w")

    what = "%s: %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg)
    lf.write(what)
    sys.stderr.write(what)

#----------------------------------------------------------------------
# Fatal error
#----------------------------------------------------------------------
def fatal(msg):
    """
    Display error message and abort.

    Pass:
        Message
    """
    log(msg)
    sys.stderr.write(msg)
    sys.exit(1)

# To run with real database update, pass userid, pw, 'run' on cmd line
if len(sys.argv) < 3:
    sys.stderr.write("usage: Request1846.py userid pw {'run' - for non-test}\n")
    sys.exit(1)

userId   = sys.argv[1]
pw       = sys.argv[2]
testMode = True
if len(sys.argv) > 3:
    if sys.argv[3] == 'run':
        testMode = False


# Connect
try:
    conn   = cdrdb.connect()
    cursor = conn.cursor()
except cdrdb.Error, info:
    fatal("Unable to connect to database:\n%s" % str(info))

# Login
session = cdr.login(userId, pw)
if session.find("<Err") >= 0:
    fatal("Unable to login:\n%s" % session)
log("Logged in")

# Query database to find document ids to modify
qry = """
------------------------------------------------------
-- Create a temporary table with the last versions that were:
--   Publishable (LastPub).
--   Either publishable or not (LastVer)
-- Table is limited to:
--   CTGovProtocols for which CWD created by CTGovImport program
SELECT v1.id as DocID,
       MAX(v1.num) as LastPub,
       MAX(v2.num) as LastVer
  INTO #alantemp
  FROM doc_version v1
  JOIN doc_version v2
    ON v1.id = v2.id
  JOIN document d
    ON v1.id = d.id
  JOIN doc_type t
    ON d.doc_type = t.id
 WHERE t.name = 'CTGovProtocol'
   -- Finds last publishable version --
   AND v1.publishable = 'Y'
   -- But only for docs for which the CWD created by import --
   AND d.comment = 'ImportCTGovProtocols: creating new CWD'
 GROUP BY v1.id
"""
try:
    log("Executing query:\n%s" % qry)
    cursor.execute(qry)
except cdrdb.Error, info:
    fatal("Unable to perform first select:\n%s" % str(info))

qry="""
------------------------------------------------------
-- Create a table of version numbers for
--   Last imported publishable version
--   Last imported non-publishable version
--   Last manually created (publishable or not)
-- For all docs for which the CWD is imported
SELECT v1.id as DocID,
       MAX(v1.num) as LastImportPub,
       MAX(v2.num) as LastImportNonPub,
       MAX(v3.num) as LastManual
  INTO #alantemp2
  FROM doc_version v1
  JOIN doc_version v2
    ON v1.id = v2.id
  JOIN doc_version v3
    ON v1.id = v3.id
  JOIN document d
    ON v1.id = d.id
  JOIN doc_type t
    ON d.doc_type = t.id
 WHERE t.name = 'CTGovProtocol'
   AND v1.comment LIKE 'ImportCTGovProtocols: %'
   AND v1.publishable = 'Y'
   AND v2.comment LIKE 'ImportCTGovProtocols: %'
   AND v2.publishable = 'N'
   AND v3.comment NOT LIKE 'ImportCTGovProtocols: %'
   AND d.comment = 'ImportCTGovProtocols: creating new CWD'
 GROUP BY v1.id, d.comment
 ORDER BY v1.id
"""

try:
    log("Executing query:\n%s" % qry)
    cursor.execute(qry)
except cdrdb.Error, info:
    fatal("Unable to perform second select:\n%s" % str(info))

qry="""
------------------------------------------------------
-- From the tables, select doc ids (and version numbers for review)
--   for which a non-pub version is the current version
--   but do not include any for which the last version was
--   manually created.
-- These will be updated
SELECT t.DocId FROM #alantemp t
  JOIN #alantemp2 t2
    ON t.DocId = t2.DocId
 WHERE t.LastVer > t.LastPub
   AND NOT (
            t2.LastManual > t2.LastImportPub
        AND
            t2.LastManual > LastImportNonPub
           )
 ORDER BY t.DocId
"""

try:
    log("Executing query:\n%s" % qry)
    cursor.execute(qry)
    docIds = [row[0] for row in cursor.fetchall()]
    log("Retrieved %d doc ids" % len(docIds))
except cdrdb.Error, info:
    fatal("Unable to select documents to version:\n%s" % str(info))

for i in docIds:
    print i

# DEBUG
# sys.exit()

# Associate this message with the versioning
updMsg = "Global creation of publishable versions from imported CTGovProtocols"

# Stats
successCnt = 0
failCnt    = 0
totalCnt   = len(docIds)

# DEBUG
# docIds = docIds[:2]

# Process each document
for docId in docIds:

    docIdStr = cdr.exNormalize(docId)[0]
    log("Processing %s" % docIdStr)

    # Avoid storing non-pub version if doc is invalid
    result = cdr.valDoc(session, "CTGovProtocol", docId=docId)
    errs   = cdr.getErrors(result, errorsExpected=False)
    if not errs:
        result = cdr.getDoc(session, docIdStr, checkout='Y')
        errs   = cdr.getErrors(result, errorsExpected=False)
        if not errs and not testMode:
            result = cdr.repDoc(session, doc=result, comment=updMsg,
                                checkIn='Y', val='Y', reason=updMsg,
                                ver='Y', verPublishable='Y')
            errs   = cdr.getErrors(result, errorsExpected=False)

        # Ensure unlock of doc not stored
        else:
            unlockErrs = cdr.unlock(session, docIdStr)
            if unlockErrs:
                log("Error unlocking document %d\n%s" % (docId, str(errs)))

    # Report results
    if errs:
        log("Error processing document %d\n%s" % (docId, str(errs)))
        failCnt += 1
    else:
        log("Created publishable version of %s, testonly=%s" % \
            (docIdStr, testMode))
        successCnt += 1

# Final report
log("""
=============
Final results:
       Documents selected: %d
   Successfully processed: %d
        Failed processing: %d
""" % (totalCnt, successCnt, failCnt))
lf.close()
