#----------------------------------------------------------------------
#
# $Id$
#
# Utility for adding new CDR Spanish summary documents translated
# in Trados.
#
#----------------------------------------------------------------------
import cdr, sys

if len(sys.argv) != 4:
    sys.stderr.write("usage: add-translated-doc.py uid pwd path-to-xml\n")
    sys.exit(1)
uid, pwd, path = sys.argv[1:]
session = cdr.login(uid, pwd)
err = cdr.checkErr(session)
if err:
    sys.stderr.write("login: %s\n" % repr(err))
    sys.exit(1)
xml = open(path, "rb").read()
doc = cdr.Doc(xml, "Summary", encoding="utf-8")
reason = "Creating document translated in Trados"
docId, warnings = cdr.addDoc(session, doc=str(doc), comment=reason, checkIn="Y",
                             reason=reason, ver="Y", verPublishable="N",
                             showWarnings=True)
if docId:
    print "added", docId
if warnings:
    print repr(warnings)
