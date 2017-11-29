#!/usr/bin/env python
#----------------------------------------------------------------------
#
# Unlock a document by its doc id.
#
#----------------------------------------------------------------------
import cdr, sys

if len(sys.argv) != 4:
    sys.stderr.write("usage: UnlockCdrDoc userId pw docId\n")
    sys.exit(1)

session = cdr.login(sys.argv[1], sys.argv[2])
if session.find("<Err") != -1:
    sys.stderr.write("Failure logging in to CDR: %s" % session)
    sys.exit(1)

# Accept doc id in any form, normalize to CDR000... form
docId = cdr.exNormalize(sys.argv[3])[0]

err = cdr.unlock(session, docId)
if err:
    sys.stderr.write("Failure unlocking %s: %s" % (docId, err))
else:
    print "unlocked " + docId
