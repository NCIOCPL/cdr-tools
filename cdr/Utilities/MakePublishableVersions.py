import cdr, sys

if len(sys.argv) < 5 or sys.argv[3] not in ('Y', 'N'):
    sys.stderr.write(
            "usage: MakePublishableVersions uid pwd Y|N doc-id [doc-id ...]\n")
    sys.stderr.write("  where Y|N is used as checkIn flag\n")
    sys.exit(1)
uid, pwd, checkIn = sys.argv[1:4]
session = cdr.login(uid, pwd)
for id in sys.argv[4:]:
    doc = cdr.getDoc(session, int(id), 'Y')
    if not doc.startswith("<Errors"):
        print cdr.repDoc(session, doc = doc, checkIn = checkIn, val = 'Y',
                ver = 'Y')
    else:
        print doc
