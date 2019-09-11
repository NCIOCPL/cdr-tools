#!/usr/bin/env python
#----------------------------------------------------------
# Re-index all documents of some document type for which the document
# was saved in the last N days, where N is passed on the command line.
#
# A version of ReindexByDocType.py
#----------------------------------------------------------

import cdr, cdrdb, sys, time

if len(sys.argv) < 5:
    sys.stderr.write("""
usage: ReindexModsByDocType.py uid pwd doctype daysback
 e.g.: To reindex all protocols saved in the last 7 days do:
       ReindexModsByDocType.py uid pwd InScopeProtocol 7
""")
    sys.exit(1)

uid	= sys.argv[1]
pwd  	= sys.argv[2]
docType = sys.argv[3]
daysBack= sys.argv[4]
session = cdr.login(uid, pwd)
# conn    = cdrdb.connect('CdrGuest')
conn    = cdrdb.connect('CdrGuest')
cursor  = conn.cursor()

cursor.execute("""\
        SELECT distinct d.id
          FROM document d
          JOIN audit_trail a
            ON d.id = a.document
          JOIN doc_type t
            ON d.doc_type = t.id
          JOIN action act
            ON a.action = act.id
         WHERE t.name = '%s'
           AND act.name IN ('ADD DOCUMENT', 'MODIFY DOCUMENT')
           AND a.dt > GETDATE() - %s
      ORDER BY d.id""" % (docType, daysBack))
rows = cursor.fetchall()
print("reindexing %d documents" % len(rows))
count = 0
for row in rows:
    print("reindexing CDR%010d" % row[0])
    resp = cdr.reindex('guest', row[0])
    if resp: print(resp)

    # Pause every 50 docs (to avoid swallowing the machine? swamping sshd?)
    count += 1
    if count % 50 == 0:
        time.sleep(1)
