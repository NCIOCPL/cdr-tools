#!/usr/bin/env python3
# ----------------------------------------------------------------------
#
# Unlock a document by its doc id.
#
# ----------------------------------------------------------------------
import cdr
import sys

if len(sys.argv) != 4:
    sys.stderr.write("usage: UnlockCdrDoc userId pw docId\n")
    sys.exit(1)

session = cdr.login(sys.argv[1], sys.argv[2])
if session.find("<Err") != -1:
    sys.stderr.write("Failure logging in to CDR: %s" % session)
    sys.exit(1)

# Accept doc id in any form, normalize to CDR000... form
docId = cdr.exNormalize(sys.argv[3])[0]

try:
    cdr.unlock(session, docId)
    print("unlocked " + docId)
except Exception as e:
    sys.stderr.write(f"Failure unlocking docId: {e}\n")
