import cdr, cdrdb, sys, time

if len(sys.argv) < 4:
    sys.stderr.write(\
      "usage: ReindexByDocType uid pwd doctype {max-docs} {host} {port}\n")
    sys.exit(1)
uid	= sys.argv[1]
pwd  	= sys.argv[2]
docType = sys.argv[3]
maxDocs = len(sys.argv) > 4 and ("TOP %s " % sys.argv[4]) or ""
host    = len(sys.argv) > 5 and sys.argv[5] or cdr.DEFAULT_HOST
port    = len(sys.argv) > 6 and int(sys.argv[6]) or cdr.DEFAULT_PORT
session = cdr.login(uid, pwd, host=host, port=port)
conn    = cdrdb.connect('CdrGuest', host)
cursor  = conn.cursor()

cursor.execute("""\
        SELECT %s d.id
          FROM document d
          JOIN doc_type t
            ON t.id = d.doc_type
           AND t.name = '%s'
      ORDER BY d.id""" % (maxDocs, docType))
rows = cursor.fetchall()
print "reindexing %d documents" % len(rows)
count = 0
for row in rows:
    print "reindexing CDR%010d" % row[0]
    resp = cdr.reindex('guest', row[0], host, port)
    if resp: print resp

    # Pause every 50 docs (to avoid swallowing the machine? swamping sshd?)
    count += 1
    if count % 50 == 0:
        time.sleep(1)
