#----------------------------------------------------------------------
#
# $Id$
#
# "Before you promote to Bach, could you please run a query on
# Bach for all the summaries that have the LastReviewed attribute?"
#
# BZIssue::4849
#
#----------------------------------------------------------------------
import cdrdb, lxml.etree as etree, sys

cursor = cdrdb.connect('CdrGuest').cursor()
cursor.execute("""\
    SELECT d.id
      FROM document d
      JOIN doc_type t
        ON t.id = d.doc_type
     WHERE t.name = 'Summary'""")
rows = cursor.fetchall()
done = 0
for row in rows:
    docId = row[0]
    cursor.execute("SELECT xml FROM document WHERE id = ?", docId)
    docXml = cursor.fetchall()[0][0]
    if 'LastReviewed' in docXml:
        tree = etree.XML(docXml.encode('utf-8'))
        if tree.findall('.//*[@LastReviewed]'):
            print "CDR%d" % row[0]
    done += 1
    sys.stderr.write("\rprocessed %d of %d summaries" % (done, len(rows)))
