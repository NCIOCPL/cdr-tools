#----------------------------------------------------------------------
#
# $Id: SaveUnversionedChanges.py,v 1.3 2008-11-03 15:53:29 bkline Exp $
#
# Save changes which haven't been versioned as a new version for a
# given CDR document type.
#
# $Log: not supported by cvs2svn $
# Revision 1.2  2008/11/03 15:46:15  bkline
# Added missing docType string interpolation in last SQL query.
#
# Revision 1.1  2008/10/31 19:18:18  bkline
# Command-line utility for saving unversioned changes in CDR documents.
#
#----------------------------------------------------------------------
import cdr, cdrdb, re, sys

LOGFILE = cdr.DEFAULT_LOGDIR + "/SaveUnversionedChanges.log"
COMMENT = "Versioning unversioned changes"

#----------------------------------------------------------------------
# Record what's happening and display it for the operator.
#----------------------------------------------------------------------
def report(what):
    sys.stderr.write(what + "\n")
    cdr.logwrite(what, LOGFILE)

#----------------------------------------------------------------------
# Get the XML for the version (possibly CWD) specified, with whitespace
# normalized.
#----------------------------------------------------------------------
def getNormalizedXml(cursor, docId, docVer = None):
    if docVer:
        cursor.execute("""\
            SELECT xml
              FROM doc_version
             WHERE id = ?
               AND num = ?""", (docId, docVer))
    else:
        cursor.execute("SELECT xml FROM document WHERE id = ?", docId)
    return re.sub("\\s+", " ", cursor.fetchall()[0][0].strip())

#----------------------------------------------------------------------
# Create a new version for a document.
#----------------------------------------------------------------------
def versionChanges(session, docId):
    report("saving unversioned changes for CDR%d" % docId)
    doc = cdr.getDoc(session, docId, 'Y')
    err = cdr.checkErr(doc)
    if err:
        report("failure for CDR%d: %s" % (docId, err))
        return False
    docId, errors = cdr.repDoc(session, doc = doc, comment = COMMENT,
                               reason = COMMENT, val = 'Y', ver = 'Y',
                               showWarnings = 'Y', checkIn = 'Y',
                               verPublishable = 'N')
    if errors:
        for e in cdr.getErrors(errors, asSequence = True):
            report(e)
    return docId and True or False

#----------------------------------------------------------------------
# Processing starts here with setup.
#----------------------------------------------------------------------
if len(sys.argv) < 4:
    sys.stderr.write("usage: %s cdr-uid cdr-pwd doc-type-name\n" % sys.argv[0])
    sys.exit(1)
session = cdr.login(sys.argv[1], sys.argv[2])
errors = cdr.checkErr(session)
if errors:
    sys.stderr.write("login failure: %s" % errors)
    sys.exit(1)
docType = sys.argv[3]
cursor = cdrdb.connect('CdrGuest').cursor()

#----------------------------------------------------------------------
# Determine the last version number for each versioned document of
# the specified document type.  Be sure to use the document type
# for the current working document instead of the version table,
# so we do the right thing for documents whose last version was
# saved as a different document type than the current working
# document has.  The other effect of joining on the document table
# (or rather, view) is to avoid doing anything with deleted documents.
#----------------------------------------------------------------------
cursor.execute("""\
   SELECT v.id, MAX(v.num) AS num
     INTO #lastver
     FROM doc_version v
     JOIN document d
       ON d.id = v.id
     JOIN doc_type t
       ON t.id = d.doc_type
    WHERE t.name = '%s'
 GROUP BY v.id""" % docType, timeout = 300)
report("found %d versioned %s documents" % (cursor.rowcount, docType))

#----------------------------------------------------------------------
# Determine the date/time each document was last saved (with or without
# creating a version).
#----------------------------------------------------------------------
cursor.execute("""\
   SELECT a.document, MAX(a.dt) AS dt
     INTO #cwd
     FROM audit_trail a
     JOIN #lastver v
       ON v.id = a.document
     JOIN action n
       ON n.id = a.action
    WHERE n.name IN ('ADD DOCUMENT', 'MODIFY DOCUMENT')
 GROUP BY a.document""", timeout = 300)

#----------------------------------------------------------------------
# When a CDR document is saved, the date/time of the save action is
# recorded in the dt column of the audit_trail table.  If the user has
# requested that a version be created as part of the save operation,
# a row is added to the all_doc_versions table with the audit_trail.dt
# column's value copied into the all_doc_versions.updated_dt column.
# So if the updated_dt in the row for a document's most recent version
# is earlier than the dt column's value in the latest row in the
# audit_trail table for this document, then the document has been
# most recently saved without a version.  The doc_version view is built
# on the all_doc_versions table.
#----------------------------------------------------------------------
cursor.execute("""\
   SELECT c.document, c.dt, v.updated_dt, v.num
     FROM #cwd c
     JOIN #lastver lv
       ON lv.id = c.document
     JOIN doc_version v
       ON v.id = lv.id
      AND v.num = lv.num
    WHERE v.updated_dt < c.dt""", timeout = 300)
rows = cursor.fetchall()
report("%d %s documents have CWD later than the last version" % (len(rows),
                                                                 docType))

#----------------------------------------------------------------------
# Create new versions for these documents if the XML for the current
# working document (CWD) differs (other than in insignificant white-
# space) from that for the latest version of the document.
#----------------------------------------------------------------------
versioned = 0
for docId, cwdDate, lastverDate, lastVer in rows:
    report("CDR%d version %d saved %s; CWD saved %s" %
           (docId, lastVer, lastverDate, cwdDate))
    cwdXml = getNormalizedXml(cursor, docId)
    lastXml = getNormalizedXml(cursor, docId, lastVer)
    if cwdXml <> lastXml:
        if versionChanges(session, docId):
            versioned += 1

#----------------------------------------------------------------------
# Version all the document which have never been versioned at all.
#----------------------------------------------------------------------
cursor.execute("""\
    SELECT d.id
      FROM document d
      JOIN doc_type t
        ON t.id = d.doc_type
     WHERE t.name = '%s'
       AND d.id NOT IN (SELECT id FROM #lastver)""" % docType, timeout = 300)
docIds = [row[0] for row in cursor.fetchall()]
report("%d %s documents have never been versioned" % (len(docIds), docType))
for docId in docIds:
    if versionChanges(session, docId):
        versioned += 1

#----------------------------------------------------------------------
# Clean up and go home.
#----------------------------------------------------------------------
report("saved %d new versions" % versioned)
cdr.logout(session)
