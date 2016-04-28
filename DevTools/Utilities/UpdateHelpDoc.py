import cdr
import sys

def usage():
    print "usage: UpdateHelpDoc.py SESSION FILENAME"
    print "   or: UpdateHelpDoc.py UID PWD FILENAME"
    print ""
    print "where FILENAME is CDRID.xml (e.g., 999999.xml)"
    sys.exit(1)

if len(sys.argv) not in (3, 4) or not sys.argv[-1].endswith(".xml"):
    usage()
comment = "Replaced by programmer"
if len(sys.argv) == 4:
    session = cdr.login(sys.argv[1], sys.argv[2])
    filename = sys.argv[3]
else:
    session, filename = sys.argv[1:3]
try:
    doc_id = int(filename[:-4])
    fp = open(filename, "rb")
    xml = fp.read()
    fp.close()
except:
    usage()
doc_obj = cdr.getDoc(session, doc_id, checkout="Y", getObject=True)
doc_obj.xml = xml
doc = str(doc_obj)
print cdr.repDoc(session, doc=doc, val="Y", ver="Y", checkIn="Y",
                 comment=comment)
