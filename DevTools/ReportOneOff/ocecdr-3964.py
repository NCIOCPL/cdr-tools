import cdrdb
import lxml.etree as etree

class Media:
    def __init__(self, cursor, doc_id, first_pub, last_pub_ver):
        self.doc_id = doc_id
        self.first_pub = first_pub
        self.creator = None
        cursor.execute("""\
SELECT xml, dt
  FROM doc_version
 WHERE id = ?
   AND num = ?""", (doc_id, last_pub_ver))
        doc_xml, self.last_pub_ver_date = cursor.fetchall()[0]
        tree = etree.XML(doc_xml.encode("utf-8"))
        self.title = tree.find("MediaTitle").text
        self.blocked_from_vol = tree.get("BlockedFromVOL")
        for node in tree.findall("MediaSource/OriginalSource/Creator"):
            self.creator = node.text
    def report(self):
        title = self.title.encode("utf-8")
        creator = self.creator and self.creator.encode("utf-8") or ""
        first_pub = self.first_pub and str(self.first_pub)[:10] or ""
        last_pub_ver_date = str(self.last_pub_ver_date)[:10]
        blocked_from_vol = self.blocked_from_vol == "Yes" and "Y" or ""
        print "%s\tCDR%d\t%s\t%s\t%s\t%s" % (title, self.doc_id,
                                             creator, first_pub,
                                             last_pub_ver_date,
                                             blocked_from_vol)

cursor = cdrdb.connect("CdrGuest").cursor()
cursor.execute("""\
   SELECT d.id, d.first_pub, MAX(v.num)
     FROM document d
     JOIN doc_version v
       ON v.id = d.id
     JOIN query_term t
       ON t.doc_id = d.id
    WHERE v.publishable = 'Y'
      AND d.active_status = 'A'
      AND t.path = '/Media/PhysicalMedia/ImageData/ImageType'
      AND t.value in ('chart', 'diagram', 'drawing', 'photo')
 GROUP BY d.id, d.first_pub
 ORDER BY d.id""")
for doc_id, first_pub, last_pub_ver in cursor.fetchall():
    doc = Media(cursor, doc_id, first_pub, last_pub_ver)
    doc.report()
