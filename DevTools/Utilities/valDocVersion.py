#!/usr/bin/env python
##
# Validate a previous version of a document against current rules.
##
import sys, re, cdr

# Defaults
host = cdr.DEFAULT_HOST
port = cdr.DEFAULT_PORT
verNum = "Current"

# usage
if len(sys.argv) < 4:
    sys.stderr.write("""
Validate a numbered document version.
usage: valDocVersion userid pw docId {versionNumber {host {port}}}
  defaults:
    versionNumber = %s
    host          = %s
    port          = %d
""" % (verNum, host, port))
    sys.exit(1)

# Args
userId = sys.argv[1]
passwd = sys.argv[2]
docId  = sys.argv[3]
if len(sys.argv) > 4:
    verNum = sys.argv[4]
if len(sys.argv) > 5:
    host = sys.argv[5]
if len(sys.argv) > 6:
    port = int(sys.argv[6])

# Establish session
session = cdr.login(userId, passwd, host=host, port=int(port))
if session.find("<Err") >= 0:
    sys.stderr.write("Error logging in: %s\n" % cdr.getErrors(session))
    sys.exit(1)

# Get the version we want
doc = cdr.getDoc(session, docId, version=verNum, host=host, port=port)

# Got it?
if doc.startswith("<Errors"):
    errList = cdr.getErrors(doc, asSequence=True)
    sys.stderr.write("Error fetching document %d, version %s\n" \
                     % (int(docId), str(verNum)))
    for err in errList:
        sys.stderr.write(" %s\n" % err)
    sys.exit(1)

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
