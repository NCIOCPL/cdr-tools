#----------------------------------------------------------------------
#
# $Id$
#
# Unlocks all documents checked out by a user.
#
# usage: UnlockDocsForUser user-id password
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdr, cdrdb, sys

if len(sys.argv) != 3:
    sys.stderr.write("usage: UnlockDocsForUser user-id password\n")
    sys.exit(1)
conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
cursor.execute("""\
        SELECT c.id
          FROM checkout c
          JOIN usr u
            ON u.id = c.usr
         WHERE u.name = ?
           AND c.dt_in IS NULL""", sys.argv[1])
rows = cursor.fetchall()
print "unlocking %d documents" % len(rows)
if rows:
    session = cdr.login(sys.argv[1], sys.argv[2])
    if session.find("<Err") != -1:
        sys.stderr.write("Failure logging in to CDR: %s" % session)
        sys.exit(1)
    for row in rows:
        err = cdr.unlock(session, "CDR%010d" % row[0])
        if err: 
            sys.stderr.write("Failure unlocking CDR%010d: %s" % (row[0], err))
        else:
            print "unlocked CDR%010d" % row[0]
