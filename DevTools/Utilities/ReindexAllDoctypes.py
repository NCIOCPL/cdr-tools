# Re-index all documents in one of the CDR databases.
#
# Reports to terminal every 100 docs, and reports total docs to be
# indexed and actually indexed.

import cdr, cdrdb, sys, time

if len(sys.argv) < 3:
    sys.stderr.write(\
      "usage: ReindexAllDoctypes uid pwd {host} {port}\n")
    sys.exit(1)
uid	    = sys.argv[1]
pwd  	= sys.argv[2]
# host    = len(sys.argv) > 3 and sys.argv[3] or cdr.DEFAULT_HOST
host    = len(sys.argv) > 3 and sys.argv[3] or cdr.h.host['APP'][0]
port    = len(sys.argv) > 4 and int(sys.argv[4]) or cdr.DEFAULT_PORT
session = cdr.login(uid, pwd, host=host, port=port)
# conn    = cdrdb.connect('CdrGuest', host)
conn    = cdrdb.connect('CdrGuest')
cursor  = conn.cursor()

cursor.execute("""\
        SELECT id
          FROM document
      ORDER BY id""")
rows = cursor.fetchall()
print "reindexing %d documents" % len(rows)
count = 0
for row in rows:
    resp = cdr.reindex('guest', row[0], host, port)
    if resp: print resp

    # Count and report
    count += 1
    if count % 100 == 0:
        print("Completed %d docs, last doc processed = CDR%010d" % (count,
               row[0]))

print("Completed reindex of %d total documents" % count)
