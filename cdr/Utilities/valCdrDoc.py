##
# Validate a single document against current rules.
#
# The document may come from the all_docs table, the doc_version table,
#   or from a file.
#
# This program is based on the earlier valDocVersion.py, renamed and modified.
#
# $Id: valCdrDoc.py,v 1.1 2007-11-29 15:39:48 ameyer Exp $
#
# $Log: not supported by cvs2svn $
##
import sys, re, cdr

# Defaults
host    = cdr.DEFAULT_HOST
port    = cdr.DEFAULT_PORT
verNum  = "Current"
fname   = None
docId   = None
doc     = None
docType = None

# usage
if len(sys.argv) < 4:
    sys.stderr.write("""
Validate a document.
usage: valCdrDoc.py userid pw doc-or-Id {version-or-type {host {port}}}
  If doc-or-id is numeric, it is assumed to be a docId.
  If doc-or-id contains at least one non-numeric, then:
     It is assumed to be the name of a file containing the document.
     If version-or-type exists:
        It must be the document type string.
     Else:
        The document in the file must include a CdrDoc wrapper with
        a valid doctype "Type" attribute.
  defaults:
    versionNumber = %s
    host          = %s
    port          = %d
""" % (verNum, host, port))
    sys.exit(1)

# Args
userId = sys.argv[1]
passwd = sys.argv[2]

# Was a docId or a filename passed?
try:
    docId = int(sys.argv[3])
except ValueError:
    fname = sys.argv[3]
    docId = None

# If filename passed, get optional doctype
if len(sys.argv) > 4:
    if fname:
        docType = sys.argv[4]
    else:
        verNum = sys.argv[4]

if len(sys.argv) > 5:
    host = sys.argv[5]
if len(sys.argv) > 6:
    port = sys.argv[6]

# Establish session
session = cdr.login(userId, passwd, host=host, port=int(port))
if session.find("<Err") >= 0:
    sys.stderr.write("Error logging in: %s\n" % cdr.getErrors(session))
    sys.exit(1)

# Get the document by id or filename
if fname:
    # From file
    try:
        fp  = open(fname)
        doc = fp.read()
        fp.close()
    except IOError, info:
        sys.stderr.write("IOError: %s" % str(info))
        sys.exit(1)

else:
    # From database
    doc = cdr.getDoc(session, docId, version=verNum, host=host, port=port)

    # Got it?
    if doc.startswith("<Errors"):
        errList = cdr.getErrors(doc, asSequence=True)
        sys.stderr.write("Error fetching document %d, version %s\n" \
                         % (int(docId), str(verNum)))
        for err in errList:
            sys.stderr.write(" %s\n" % err)
        sys.exit(1)

if not docType:
    # Find document type from CdrDoc@Type attribute
    match = re.search(r"""<CdrDoc Type=['"](?P<doctype>[A-za-z]+)['"]""", doc)
    if not match:
        sys.stderr.write("Bad result from cdr.getDoc.  No doc type found\n")
        sys.exit(1)
    docType = match.group("doctype")

# Execute validation on doc
result = cdr.valDoc(session, docType, doc=doc, host=host, port=port)

errList = cdr.getErrors(result, errorsExpected=False, asSequence=True)
if not errList or len(errList) == 0:
    print("No validation errors")
else:
    for err in errList:
        print(" %s\n" % err)
