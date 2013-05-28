import cdrdb, sys

cursor = cdrdb.connect('CdrGuest').cursor()
cursor.execute("""\
    SELECT xml
      FROM ctgov_import
     WHERE nlm_id = ?""", sys.argv[1])
docXml = cursor.fetchall()[0][0]
fp = open(sys.argv[1] + '.xml', 'wb')
fp.write(docXml.encode('utf-8'))
fp.close()
print "wrote '%s.xml'" % sys.argv[1]
