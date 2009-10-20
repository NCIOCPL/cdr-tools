#======================================================================
#
# $Id$
#
# Fetch a list of who can do what.
#
# $Log: not supported by cvs2svn $
#======================================================================

import cdrdb, sys
pattern = len(sys.argv) > 1 and sys.argv[1] or '%'
host    = len(sys.argv) > 2 and sys.argv[2] or 'localhost'
conn    = cdrdb.connect(dataSource = host)
cursor  = conn.cursor()
cursor.execute("""\
    SELECT DISTINCT a.name ActionName,
                    g.name GroupName,
                    u.name UserName
               FROM usr u
               JOIN grp_usr gu
                 ON gu.usr = u.id
               JOIN grp g
                 ON g.id = gu.grp
               JOIN grp_action ga
                 ON ga.grp = g.id
               JOIN action a
                 ON a.id = ga.action
              WHERE a.name LIKE '%s'
           ORDER BY ActionName, GroupName, UserName""" % pattern)
for row in cursor.fetchall():
    print "\t".join(row)
