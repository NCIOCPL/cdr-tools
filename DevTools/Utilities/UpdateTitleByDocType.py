#----------------------------------------------------------
# Regenerate and update document table titles for all docs of a
# given doctype.
#
# $Id$
#
# $Log: not supported by cvs2svn $
#
#----------------------------------------------------------
import cdr, cdrdb, sys, time

if len(sys.argv) < 4:
    sys.stderr.write(\
      "usage: UpdateTitleByDocType uid pwd doctype {max-docs} {host} {port}\n")
    sys.exit(1)
uid	    = sys.argv[1]
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
    sys.stdout.write("Updating title for CDR%010d" % row[0])
    resp = cdr.updateTitle('guest', row[0], host, port)
    if resp:
        print(" - changed")
    else:
        print(" - no change needed")

    # Pause every so many docs (to avoid swamping the machine or sshd)
    # We had a problem at one time that this fixed - though it may
    #   not be needed any more
    count += 1
    if count % 50 == 0:
        time.sleep(1)
