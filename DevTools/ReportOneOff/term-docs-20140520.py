import cdrdb
import sys

cursor = cdrdb.connect("CdrGuest").cursor()
cursor.execute("""\
SELECT c.id
  FROM pub_proc_cg c
  JOIN document d
    ON d.id = c.id
  JOIN doc_type t
    ON t.id = d.doc_type
 WHERE t.name = 'Term'""")
doc_ids = [row[0] for row in cursor.fetchall()]
done = 0
for doc_id in doc_ids:
    cursor.execute("SELECT xml FROM pub_proc_cg WHERE id = ?", doc_id)
    doc_xml = cursor.fetchall()[0][0]
    fp = open("term-docs-20140520/CDR%d.xml" % doc_id, "wb")
    fp.write(doc_xml.encode("utf-8"))
    fp.close()
    done += 1
    sys.stderr.write("\r%d of %d" % (done, len(doc_ids)))
sys.stderr.write("\n")
