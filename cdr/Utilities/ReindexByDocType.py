import cdr, cdrdb, sys

if len(sys.argv) < 2:
    sys.stderr.write("usage: ReindexByDocType doc-type-name [max-docs]\n")
    sys.exit(1)
maxDocs = len(sys.argv) > 2 and ("TOP %s " % sys.argv[2]) or ""
docType = sys.argv[1]
session = cdr.login('rmk', '***REDACTED***')
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
