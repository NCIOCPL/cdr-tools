import cdr, cdrdb, sys

if len(sys.argv) < 4:
    sys.stderr.write("usage: ReindexByDocType uid pwd doctype [max-docs]\n")
    sys.exit(1)
uid	= sys.argv[1]
pwd  	= sys.argv[2]
docType = sys.argv[3]
maxDocs = len(sys.argv) > 4 and ("TOP %s " % sys.argv[4]) or ""
session = cdr.login(uid, pwd)
conn    = cdrdb.connect('CdrGuest')
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
for row in rows:
    print "reindexing CDR%010d" % row[0]
    resp = cdr.reindex('guest', row[0])
    if resp: print resp
