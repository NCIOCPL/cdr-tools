#----------------------------------------------------------------------
#
# $Id$
#
# Undo testing actions so we can do it again.
#
# BZIssue::4926
#
#----------------------------------------------------------------------
import cdrdb, cdr, sys, lxml.etree as etree

def boolToYN(val):
    return val and 'Y' or 'N'

def rollBackDoc(session, docId, ver, makeVer, makePub, comment):
    doc = cdr.getDoc(session, docId, version=ver, checkout='Y', getObject=True)
    error = cdr.checkErr(doc)
    if error:
        raise Exception(error)
    comment = "Replacing CWD with version %d: %s" % (ver, comment)
    val = makePub and 'Y' or 'N'
    response = cdr.repDoc(session, doc=str(doc), checkIn='Y', val=val,
                          ver=boolToYN(makeVer),
                          verPublishable=boolToYN(makePub),
                          comment=comment, reason=comment, showWarnings=True)
    errors = cdr.getErrors(response[1], asSequence=True, errorsExpected=False)
    if not response[0]:
        raise Exception("CDR%s: document save failure", errors)
    return errors

def hasPronunciationLinks(docXml):
    tree = etree.XML(docXml.encode('utf-8'))
    if tree.findall("TermName/MediaLink/MediaID"):
        return True
    if tree.findall("TranslatedName/MediaLink/MediaID"):
        return True
    return False

def findPreTestVersion(docId):
    cursor.execute("SELECT MAX(num) FROM doc_version WHERE id = ?", docId)
    lastVersion = cursor.fetchall()[0][0]
    version = lastVersion
    while version > 0:
        cursor.execute("""\
SELECT xml, publishable
  FROM doc_version
 WHERE id = ?
   AND num = ?""", (docId, version))
        docXml, publishable = cursor.fetchall()[0]
        if not hasPronunciationLinks(docXml):
            if version == lastVersion:
                raise Exception("CDR%d: last version (%d) has no pronunciation"
                                " links" % (docId, version))
            return version, publishable == 'Y'
        version -= 1
    raise Exception("CDR%d: no version found without pronunciation links" %
                    docId)

if len(sys.argv) != 3:
    sys.stderr.write("usage: %s uid pwd" % sys.argv[0])
    sys.exit(1)
uid, pwd = sys.argv[1:]
session = cdr.login(uid, pwd)
error = cdr.checkErr(session)
if error:
    raise Exception("login: %s" % error)
cursor = cdrdb.connect('CdrGuest').cursor()
cursor.execute("""\
SELECT DISTINCT doc_id
           FROM query_term
          WHERE path LIKE '/GlossaryTermName/%Name/MediaLink/MediaID/@cdr:ref'
""")
docIds = [row[0] for row in cursor.fetchall()]
comment = 'rolling back testing for task 4926'
for docId in docIds:
    try:
        version, publishable = findPreTestVersion(docId)
    except Exception, e:
        print "CDR%s: %s" % (docId, e)
        continue
    try:
        errors = rollBackDoc(session, docId, version, True, publishable,
                             comment)
        if errors:
            print "CDR%d warnings: %s" % (docId, errors)
        else:
            print "CDR%d: success" % docId
    except Exception, e:
        print "CDR%d failure: %s" % (docId, e)
cursor.execute("""\
SELECT id
  FROM document
 WHERE comment = 'document created for CDR task 4926'""")
docIds = [row[0] for row in cursor.fetchall()]
for docId in docIds:
    result = cdr.delDoc(session, cdr.normalize(docId), reason=comment)
    error = cdr.checkErr(result)
    if error:
        print "deleting CDR%d: %s" % (docId, error)
    else:
        print "deleted media document CDR%d" % docId
