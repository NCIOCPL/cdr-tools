#----------------------------------------------------------------------
# $Id$
# Script to block trials identified by the find-obsolete-trial-documents.py
# script. See the notes at the top of that script for more information.
# Run as part of the Egyptian Mau release.
#----------------------------------------------------------------------
import cdr
import sys

DEFAULT = "obsolete-trials-to-drop.txt"
id_file = len(sys.argv) > 3 and sys.argv[3] or DEFAULT
session = cdr.login(sys.argv[1], sys.argv[2])
doc_ids = [int(line.strip()) for line in open(id_file)]
done = 0
comment = "blocking obsolete trial document"
for doc_id in doc_ids:
    try:
        cdr.setDocStatus(session, doc_id, "I", comment=comment)
    except Exception, e:
        sys.stderr.write("\n%d: %s\n" % (doc_id, e))
    done += 1
    sys.stderr.write("\rblocked %d of %d" % (done, len(doc_ids)))
