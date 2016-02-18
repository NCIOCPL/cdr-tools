#----------------------------------------------------------------------
#
# $Id$
#
# Utility for adding new CDR Spanish summary documents translated
# in Trados.
#
#----------------------------------------------------------------------
import cdr, sys

if len(sys.argv) != 3:
    sys.stderr.write("usage: add-translated-doc.py session path-to-xml\n")
    sys.exit(1)
session, path = sys.argv[1:]
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
