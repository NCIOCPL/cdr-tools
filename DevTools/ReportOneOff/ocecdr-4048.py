#----------------------------------------------------------------------
# Custom report of English summaries which do not have the new PMID
# element.
#----------------------------------------------------------------------

# Standard library modules
import lxml.etree as etree
import sys

# Custom, application-specific modules
import cdrdb

cursor = cdrdb.connect("CdrGuest").cursor()
cursor.execute("""\
SELECT doc_id
  FROM query_term_pub
  JOIN active_doc
    ON id = doc_id
 WHERE path = '/Summary/SummaryMetaData/SummaryLanguage'
   AND value = 'English'""")
ids = [row[0] for row in cursor.fetchall()]
done = 0
for cdr_id in sorted(ids):
    try:
        cursor.execute("SELECT xml FROM document WHERE id = ?", cdr_id)
        root = etree.XML(cursor.fetchall()[0][0].encode("utf-8"))
        pmid = root.find("SummaryMetaData/PMID")
        if pmid is None:
            print "%s: PMID element not found" % cdr_id
            #print etree.tostring(root, pretty_print=True)
            #break
        elif pmid.text is None:
            print "%s: PMID text content is empty" % cdr_id
        elif len(pmid.text) != 8:
            print "%s: PMID is %s" % (cdr_id, repr(pmid.text))
    except Exception, e:
        print "%s: %s" % (cdr_id, e)
    done += 1
    sys.stderr.write("\r%d of %d processed" % (done, len(ids)))
sys.stderr.write("\n")
