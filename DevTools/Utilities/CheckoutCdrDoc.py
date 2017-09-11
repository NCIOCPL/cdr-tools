import cdr
import sys

if len(sys.argv) == 4:
    session = cdr.login(sys.argv[1], sys.argv[2])
    cdr_id = sys.argv[3]
else:
    session, cdr_id = sys.argv[1:3]
print cdr.getDoc(session, cdr_id, "Y")
