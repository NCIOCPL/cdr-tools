#----------------------------------------------------------------------
#
# $Id: fix-non-us-addresses.py,v 1.1 2003-01-21 14:29:19 bkline Exp $
#
# Change AddressType attributes of "Non US" to "Non-US" so we can
# take advantage of the DTD support for attribute valid value
# picklists.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdrdb, xml.dom.minidom, sys, cdr, re, time

#----------------------------------------------------------------------
# Here's the pattern we want to replace.
#----------------------------------------------------------------------
pattern = re.compile(r"(AddressType\s*=\s*([\"'])Non US\2)")

#----------------------------------------------------------------------
# Here the new string we want to replace it with.
#----------------------------------------------------------------------
newValue = "AddressType='Non-US'"

#----------------------------------------------------------------------
# Global variable for the current doc ID; used by callback function below.
#----------------------------------------------------------------------
docId = None

#----------------------------------------------------------------------
# Callback function which logs the replacement and proved the new value.
#----------------------------------------------------------------------
def replace(match):
    global logFile
    global docId
    global newValue
    logFile.write("CDR%010d: replacing %s with %s\n" % (docId,
                                                        match.group(1),
                                                        newValue))
    return newValue

#----------------------------------------------------------------------
# Function to fix a document.
#----------------------------------------------------------------------
def fixDoc(doc):
    return re.sub(pattern, replace, doc)
    
#----------------------------------------------------------------------
# Log the disposition of one document to standard output.
#----------------------------------------------------------------------
def logDoc(id, disposition):
    print "%s: CDR%010d: %s" % (time.strftime("%Y-%m-%d %H:%M:%S"),
                                id, disposition)

#----------------------------------------------------------------------
# Check command-line arguments.
#----------------------------------------------------------------------
if len(sys.argv) != 3:
    sys.stderr.write("usage: fix-non-us-addresses uid pwd\n")
    sys.exit(1)
usr = sys.argv[1]
pwd = sys.argv[2]

#----------------------------------------------------------------------
# Create the string we'll use to document what we've done.
#----------------------------------------------------------------------
reason = "Modified by script cdr/Utilities/fix-non-us-addresses.py"

#----------------------------------------------------------------------
# Create the file we'll use to log the lines we're going to change.
#----------------------------------------------------------------------
logFile = open("fix-non-us-addresses.fixed-lines", "a")

#----------------------------------------------------------------------
# These are the document types we work on.
#----------------------------------------------------------------------
typs = ('InScopeProtocol', 'Person', 'Organization')

#----------------------------------------------------------------------
# Establish a CDR session.
#----------------------------------------------------------------------
sess = cdr.login(usr, pwd)
if sess.find("Error") != -1:
    sys.stderr.write("cdr.login(): %s\n" % sess)
    sys.exit(1)
sys.stderr.write("logged in...\n")

#----------------------------------------------------------------------
# Connect to the database
#----------------------------------------------------------------------
conn = cdrdb.connect()
curs = conn.cursor()
conn.setAutoCommit(1)
sys.stderr.write("connected...\n")

#----------------------------------------------------------------------
# Find the last version (publishable or not) for all documents.
#----------------------------------------------------------------------
curs.execute("""\
          SELECT d.id, MAX(v.num) AS ver, t.name AS doc_type
            INTO #LastVersion
            FROM document d
            JOIN doc_type t
              ON t.id = d.doc_type
 LEFT OUTER JOIN doc_version v
              ON v.id = d.id
        GROUP BY d.id, t.name""", timeout=300)
sys.stderr.write("#LastVersion created...\n")

#----------------------------------------------------------------------
# Find the last publishable version for all the documents.
#----------------------------------------------------------------------
try:
    curs.execute("""\
          SELECT d.id, MAX(v.num) AS ver, t.name AS doc_type
            INTO #LastPublishableVersion
            FROM document d
            JOIN doc_type t
              ON t.id = d.doc_type
 LEFT OUTER JOIN doc_version v
              ON v.id = d.id
             AND v.publishable = 'Y'
        GROUP BY d.id, t.name""", timeout=300)
except:
    pass # ignore warning (which throws an exception)
sys.stderr.write("#LastPublishableVersion created...\n")

#----------------------------------------------------------------------
# Find out when the current working copy was last saved.
#----------------------------------------------------------------------
curs.execute("""\
          SELECT t.document as id, MAX(t.dt) AS dt
            INTO #CurrentWorkingVersion
            FROM audit_trail t
            JOIN action a
              ON a.id = t.action
           WHERE a.name IN ('ADD DOCUMENT', 'MODIFY DOCUMENT')
        GROUP BY t.document""", timeout=300)
sys.stderr.write("#CurrentWorkingVersion created...\n")

#----------------------------------------------------------------------
# Find out how many documents of each type have no version at all.
#----------------------------------------------------------------------
curs.execute("""\
          SELECT COUNT(*), doc_type
            FROM #LastVersion
           WHERE ver IS NULL
        GROUP BY doc_type""", timeout=300)
unVersioned = curs.fetchall()
sys.stderr.write("null counts from #LastVersion fetched...\n")

#----------------------------------------------------------------------
# Find out how many documents of each type have no publishable version.
#----------------------------------------------------------------------
curs.execute("""\
          SELECT COUNT(*), doc_type
            FROM #LastPublishableVersion
           WHERE ver IS NULL
        GROUP BY doc_type""", timeout=300)
noPubVersions = curs.fetchall()
sys.stderr.write("null counts from #LastPublishableVersion fetched...\n")

#----------------------------------------------------------------------
# Find out how many documents of each type we have in total.
#----------------------------------------------------------------------
curs.execute("""\
          SELECT COUNT(*), doc_type
            FROM #LastVersion
        GROUP BY doc_type""", timeout=300)
totals = curs.fetchall()
sys.stderr.write("total counts from #LastVersion fetched...\n")

#----------------------------------------------------------------------
# Show the counts per doc type of unversioned documents.
#----------------------------------------------------------------------
for row in unVersioned:
    if row[1] in typs:
        print "%d %s documents have no version" % (row[0], row[1])
sys.stderr.write("unversioned counts printed...\n")

#----------------------------------------------------------------------
# Show the counts per doc type of docs with no publishable version.
#----------------------------------------------------------------------
for row in noPubVersions:
    if row[1] in typs:
        print "%d %s documents have no publishable version" % (row[0], row[1])
sys.stderr.write("unpublishable counts printed...\n")

#----------------------------------------------------------------------
# Show the counts of all documents per document type.
#----------------------------------------------------------------------
for row in totals:
    if row[1] in typs:
        print "%d %s documents in all" % (row[0], row[1])
sys.stderr.write("total counts printed...\n")

#----------------------------------------------------------------------
# Just in a case a previous run aborted.
#----------------------------------------------------------------------
try:
    curs.execute("""DROP TABLE xxx_please_drop_me""")
except:
    pass

#----------------------------------------------------------------------
# Now we change the documents; handle one doc type at a time.
#----------------------------------------------------------------------
for docType in typs:
    sys.stderr.write("top of loop for %s documents...\n" % docType)

    #------------------------------------------------------------------
    # Process the documents which have no version at all.
    #------------------------------------------------------------------
    curs.execute("""\
          SELECT d.id
            INTO xxx_please_drop_me
            FROM document d
            JOIN #LastVersion v
              ON v.id = d.id
           WHERE v.ver IS NULL
             AND v.doc_type = ?""", docType, timeout=300)
    sys.stderr.write("created table xxx_please_drop_me (%d rows)...\n" %
                     curs.rowcount)
    curs.execute("""\
          SELECT d.id
            FROM document d
            JOIN xxx_please_drop_me x
              ON x.id = d.id
           WHERE d.xml LIKE '%Non US%'""", timeout = 500)
    rows = curs.fetchall()
    sys.stderr.write("%d rows fetched for set 1...\n" % len(rows))
    curs.execute("DROP TABLE xxx_please_drop_me")
    sys.stderr.write("dropped table xxx_please_drop_me...\n")
    print ("%d %s unversioned docs with 'Non US':" % (len(rows), docType))
    for row in rows:
        resp = cdr.getDoc(sess, row[0], 'Y')
        if resp.startswith("<Errors"):
            logDoc(row[0], resp)
        else:
            docId = row[0]
            doc = fixDoc(resp)
            resp = cdr.repDoc(sess, doc = doc, comment = reason,
                              reason = reason, showWarnings = 1,
                              checkIn = 'Y', val = 'Y')
            if not resp[0]:
                logDoc(row[0], resp[1])
            elif resp[1]:
                logDoc(row[0], "document fixed with warnings: %s" % resp[1])
            else:
                logDoc(row[0], "document fixed")
    sys.stderr.write("unversioned docs fixed...\n")

    #------------------------------------------------------------------
    # Fix the documents for which we can create a new version.
    #------------------------------------------------------------------
    curs.execute("""\
          SELECT d.id, v.publishable
            INTO xxx_please_drop_me
            FROM document d
            JOIN #LastVersion l
              ON l.id = d.id
            JOIN doc_version v
              ON v.id = l.id
             AND v.num = l.ver
            JOIN #CurrentWorkingVersion c
              ON c.id = v.id
             AND c.dt = v.updated_dt
           WHERE l.doc_type = ?""", docType, timeout=300)
    sys.stderr.write("created table xxx_please_drop_me (%d rows)...\n" %
                     curs.rowcount)
    curs.execute("""\
          SELECT d.id, x.publishable
            FROM document d
            JOIN xxx_please_drop_me x
              ON x.id = d.id
           WHERE d.xml LIKE '%Non US%'""", timeout=500)
    rows = curs.fetchall()
    sys.stderr.write("%d rows fetched for set 2...\n" % len(rows))
    curs.execute("DROP TABLE xxx_please_drop_me")
    sys.stderr.write("dropped table xxx_please_drop_me...\n")
    print ("%d %s docs, last ver unchanged, with 'Non US':" %
           (len(rows), docType))
    for row in rows:
        resp = cdr.getDoc(sess, row[0], 'Y')
        if resp.startswith("<Errors"):
            logDoc(row[0], resp)
        else:
            docId = row[0]
            doc = fixDoc(resp)
            publishable = row[1].encode('ascii')
            resp = cdr.repDoc(sess, doc = doc, comment = reason, ver = 'Y',
                              reason = reason, showWarnings = 1,
                              verPublishable = publishable, checkIn = 'Y',
                              val = 'Y')
            if not resp[0]:
                logDoc(row[0], resp[1])
            elif resp[1]:
                logDoc(row[0], "document fixed with warnings: %s" % resp[1])
            else:
                logDoc(row[0], "document fixed (publishable='%s')" % row[1])
    sys.stderr.write("versionable docs fixed...\n")

    #------------------------------------------------------------------
    # Fix the versioned documents for which we can't create a new version.
    #------------------------------------------------------------------
    curs.execute("""\
          SELECT d.id
            INTO xxx_please_drop_me
            FROM document d
            JOIN #LastVersion l
              ON l.id = d.id
            JOIN doc_version v
              ON v.id = l.id
             AND v.num = l.ver
            JOIN #CurrentWorkingVersion c
              ON c.id = d.id
           WHERE c.dt <> v.updated_dt
             AND l.doc_type = ?""", docType, timeout=300)
    sys.stderr.write("created table xxx_please_drop_me (%d rows)...\n" % 
                     curs.rowcount)
    curs.execute("""\
          SELECT d.id
            FROM document d
            JOIN xxx_please_drop_me x
              ON x.id = d.id
           WHERE d.xml LIKE '%Non US%'""", timeout=500)
    rows = curs.fetchall()
    sys.stderr.write("%d rows fetched for set 3...\n" % len(rows))
    curs.execute("DROP TABLE xxx_please_drop_me")
    sys.stderr.write("dropped table xxx_please_drop_me...\n")
    print ("%d %s docs, last ver changed, with 'Non US':" %
           (len(rows), docType))
    for row in rows:
        resp = cdr.getDoc(sess, row[0], 'Y')
        if resp.startswith("<Errors"):
            logDoc(row[0], resp)
        else:
            docId = row[0]
            doc = fixDoc(resp)
            resp = cdr.repDoc(sess, doc = doc, reason = reason,
                              comment = reason, showWarnings = 1,
                              checkIn = 'Y', val = 'Y')
            if not resp[0]:
                logDoc(row[0], resp[1])
            elif resp[1]:
                logDoc(row[0], "document fixed with warnings: %s" % resp[1])
            else:
                logDoc(row[0], "document fixed")
    sys.stderr.write("unversionable docs fixed...\n")
