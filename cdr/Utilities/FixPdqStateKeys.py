import cdr, cdrdb, re, string, sys
"""<PoliticalUnit PdqStateKey="103" cdr:id="Punjab">"""

if len(sys.argv) != 3:
    print "usage: FixPdqStateKeys.py user-id password"
    sys.exit(1)
patt = re.compile('PdqStateKey="(\d+)" cdr:id="([^"]+)"')
file = open('StateIdList.txt', 'w')
sess = cdr.login(sys.argv[1], sys.argv[2])
conn = cdrdb.connect('CdrGuest')
curs = conn.cursor()
curs.execute("""
SELECT DISTINCT doc_id
           FROM query_term
          WHERE path = '/GeographicEntity/PoliticalUnit/@cdr:id'""")
for row in curs.fetchall():
    doc = cdr.getDoc(sess, row[0], 'Y')
    doc = doc.replace('PdqKey=', 'PdqStateKey=')
    for line in string.split(doc, "\n"):
        match = patt.search(line)
        if match:
            file.write("%s\t%s\n" % (match.group(1), match.group(2)))
    rsp = cdr.repDoc(sess, doc = doc, checkIn = 'Y', val = 'Y')
    print rsp
