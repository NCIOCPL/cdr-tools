#----------------------------------------------------------------------
#
# $Id$
#
# Emergency report for Lakshmi on average size of SupplementaryInfo
# attachment.
#
#----------------------------------------------------------------------
import cdrdb, operator, sys

def getBlobSize(blobId, cursor):
    try:
        cursor.execute("SELECT data FROM doc_blob WHERE id = ?", blobId)
        rows = cursor.fetchall()
        if not rows:
            print "blob %d not found" % blobId
            return None
        bytes = rows[0][0]
        n = len(bytes)
        bytes = None
        rows = None
        return n
    except Exception, e:
        print e
cursor = cdrdb.connect('CdrGuest').cursor()
cursor.execute("""\
    SELECT DISTINCT b.blob_id
      FROM doc_blob_usage b
      JOIN query_term q
        ON q.int_val = b.doc_id
      JOIN document d
        ON b.doc_id = d.id
      JOIN doc_type t
        ON t.id = d.doc_type
     WHERE q.path LIKE '/InScopeProtocol%@cdr:ref'
       AND t.name = 'SupplementaryInfo'""")
sizes = []
rows = cursor.fetchall()
print "%d blobs" % len(rows)
for row in rows:
    blobId = row[0]
    size = getBlobSize(blobId, cursor)
    if size is not None:
        sizes.append(size)
        sys.stderr.write("\rcollected %d sizes" % len(sizes))
print "%d sizes" % len(sizes)
print reduce(operator.add, sizes) / len(sizes)
