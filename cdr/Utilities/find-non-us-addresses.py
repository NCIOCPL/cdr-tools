#----------------------------------------------------------------------
#
# $Id: find-non-us-addresses.py,v 1.1 2003-01-21 14:29:19 bkline Exp $
#
# Companion reporting script for fix-non-us-address.py utility.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdrdb, xml.dom.minidom, sys

typs = ('InScopeProtocol', 'Person', 'Organization')
conn = cdrdb.connect()
curs = conn.cursor()
conn.setAutoCommit(1)
sys.stderr.write("connected...\n")
curs.execute("""\
          SELECT d.id, MAX(v.num) AS ver, t.name AS doc_type
            INTO #LastVersion
            FROM document d
            JOIN doc_type t
              ON t.id = d.doc_type
 LEFT OUTER JOIN doc_version v
              ON v.id = d.id
        GROUP BY d.id, t.name""", timeout=300)
sys.stderr.write("#LastVersion created...\n")
try:
    curs.execute("""\
          SELECT d.id, MAX(v.num) AS ver, t.name AS doc_type
            INTO #LastPublishableVersion
            FROM document d
            JOIN doc_type t
              ON t.id = d.doc_type
 LEFT OUTER JOIN doc_version v
              ON v.id = d.id
             AND v.publishable = 'Y'
        GROUP BY d.id, t.name""", timeout=300)
except:
    pass # ignore warning, which throws an exception.
sys.stderr.write("#LastPublishableVersion created...\n")
curs.execute("""\
          SELECT t.document as id, MAX(t.dt) AS dt
            INTO #CurrentWorkingVersion
            FROM audit_trail t
            JOIN action a
              ON a.id = t.action
           WHERE a.name IN ('ADD DOCUMENT', 'MODIFY DOCUMENT')
        GROUP BY t.document""", timeout=300)
sys.stderr.write("#CurrentWorkingVersion created...\n")
curs.execute("""\
          SELECT COUNT(*), doc_type
            FROM #LastVersion
           WHERE ver IS NULL
        GROUP BY doc_type""", timeout=300)
unVersioned = curs.fetchall()
sys.stderr.write("null counts from #LastVersion fetched...\n")
curs.execute("""\
          SELECT COUNT(*), doc_type
            FROM #LastPublishableVersion
           WHERE ver IS NULL
        GROUP BY doc_type""", timeout=300)
noPubVersions = curs.fetchall()
sys.stderr.write("null counts from #LastPublishableVersion fetched...\n")
curs.execute("""\
          SELECT COUNT(*), doc_type
            FROM #LastVersion
        GROUP BY doc_type""", timeout=300)
totals = curs.fetchall()
sys.stderr.write("total counts from #LastVersion fetched...\n")
for row in unVersioned:
    if row[1] in typs:
        print "%d %s documents have no version" % (row[0], row[1])
sys.stderr.write("unversioned counts printed...\n")
for row in noPubVersions:
    if row[1] in typs:
        print "%d %s documents have no publishable version" % (row[0], row[1])
sys.stderr.write("unpublishable counts printed...\n")
for row in totals:
    if row[1] in typs:
        print "%d %s documents in all" % (row[0], row[1])
sys.stderr.write("total counts printed...\n")
for docType in typs:
    sys.stderr.write("top of loop for %s documents...\n" % docType)
    curs.execute("""\
          SELECT d.id
            INTO xxx_please_drop_me
            FROM document d
            JOIN #LastVersion v
              ON v.id = d.id
           WHERE v.ver IS NULL
             AND v.doc_type = ?""", docType, timeout=300)
    sys.stderr.write("created table xxx_please_drop_me (%d rows)...\n" % curs.rowcount)
    curs.execute("""\
          SELECT d.id
            FROM document d
            JOIN xxx_please_drop_me x
              ON x.id = d.id
           WHERE d.xml LIKE '%Non US%'""", timeout = 500)
    rows = curs.fetchall()
    sys.stderr.write("%d rows fetched for set 1...\n" % len(rows))
    curs.execute("DROP TABLE xxx_please_drop_me")
    sys.stderr.write("dropped table xxx_please_drop_me...\n")
    print ("%d %s unversioned docs with 'Non US':" % (len(rows), docType))
    for row in rows:
        print row[0],
    print ""
    sys.stderr.write("ids for set 1 printed...\n")

    curs.execute("""\
          SELECT d.id
            INTO xxx_please_drop_me
            FROM document d
            JOIN #LastVersion l
              ON l.id = d.id
            JOIN doc_version v
              ON v.id = l.id
             AND v.num = l.ver
            JOIN #CurrentWorkingVersion c
              ON c.id = v.id
           WHERE c.dt = v.updated_dt
             AND l.doc_type = ?""", docType, timeout=300)
    sys.stderr.write("created table xxx_please_drop_me (%d rows)...\n" % curs.rowcount)
    curs.execute("""\
          SELECT d.id
            FROM document d
            JOIN xxx_please_drop_me x
              ON x.id = d.id
           WHERE d.xml LIKE '%Non US%'""", timeout=500)
    rows = curs.fetchall()
    sys.stderr.write("%d rows fetched for set 2...\n" % len(rows))
    curs.execute("DROP TABLE xxx_please_drop_me")
    sys.stderr.write("dropped table xxx_please_drop_me...\n")
    print ("%d %s docs, last ver unchanged, with 'Non US':" %
           (len(rows), docType))
    for row in rows:
        print row[0],
    print ""
    sys.stderr.write("ids for set 2 printed...\n")

    curs.execute("""\
          SELECT d.id
            INTO xxx_please_drop_me
            FROM document d
            JOIN #LastVersion l
              ON l.id = d.id
            JOIN doc_version v
              ON v.id = l.id
             AND v.num = l.ver
            JOIN #CurrentWorkingVersion c
              ON c.id = d.id
           WHERE c.dt <> v.updated_dt
             AND l.doc_type = ?""", docType, timeout=300)
    sys.stderr.write("created table xxx_please_drop_me (%d rows)...\n" % curs.rowcount)
    curs.execute("""\
          SELECT d.id
            FROM document d
            JOIN xxx_please_drop_me x
              ON x.id = d.id
           WHERE d.xml LIKE '%Non US%'""", timeout=500)
    rows = curs.fetchall()
    sys.stderr.write("%d rows fetched for set 3...\n" % len(rows))
    curs.execute("DROP TABLE xxx_please_drop_me")
    sys.stderr.write("dropped table xxx_please_drop_me...\n")
    print ("%d %s docs, last ver changed, with 'Non US':" %
           (len(rows), docType))
    for row in rows:
        print row[0],
    print ""
    sys.stderr.write("ids for set 3 printed...\n")

    # We insert this intermediate step because SQL Server isn't
    # smart enough to optimize the query for set 4 correctly.
    curs.execute("""\
          SELECT v.id, v.num
            INTO xxx_please_drop_me
            FROM doc_version v
            JOIN #lastPublishableVersion p
              ON p.id = v.id
             AND p.ver = v.num
            JOIN #CurrentWorkingVersion c
              ON c.id = v.id
           WHERE c.dt <> v.updated_dt
             AND p.doc_type = ?""", docType, timeout=500)
    sys.stderr.write("created table xxx_please_drop_me (%d rows)...\n" % curs.rowcount)
    curs.execute("""\
          SELECT v.id
            FROM doc_version v
            JOIN xxx_please_drop_me s
              ON s.id = v.id
             AND s.num = v.num
           WHERE v.xml LIKE '%Non US%'""", timeout=500)
    rows = curs.fetchall()
    sys.stderr.write("%d rows fetched for set 4...\n" % len(rows))
    curs.execute("DROP TABLE xxx_please_drop_me")
    sys.stderr.write("dropped table xxx_please_drop_me...\n")
    print ("%d %s docs, last pub ver changed, with 'Non US':" %
           (len(rows), docType))
    for row in rows:
        print row[0],
    print ""
    sys.stderr.write("ids for set 4 printed...\n")

## curs.execute("""\
##     SELECT DISTINCT d.id, d.xml
##                FROM document d
##                JOIN query_term q
##                  ON q.doc_id = d.id
##               WHERE q.path IN ('/InScopeProtocol/%/Country/@cdr:ref',
##                                '/Person/%/Country/@cdr:ref',
##                                '/Organization/%/Country/@cdr:ref')
##                 AND q.int_val <> 43753""")
## row = curs.fetchone()
## while row:
##     dom = xml.dom.minidom.parseString(row[1])
    
