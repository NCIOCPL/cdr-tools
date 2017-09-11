#----------------------------------------------------------------------
# Find and display all of the distinct current status values in
# CTGovProtocol documents (with counts).
#----------------------------------------------------------------------
import cdrdb
import lxml.etree as etree
import sys

query = cdrdb.Query("pub_proc_cg c", "c.xml")
query.join("document d", "d.id = c.id")
query.join("doc_type t", "t.id = d.doc_type")
query.where(query.Condition("t.name", "CTGovProtocol"))
results = query.execute()
row = results.fetchone()
statuses = {}
done = 0
while row:
    done += 1
    root = etree.XML(row[0].encode("utf-8"))
    for child in root.findall("CurrentProtocolStatus"):
        status = child.text
        statuses[status] = statuses.get(status, 0) + 1
    sys.stderr.write("\r%d parsed" % done)
    row = results.fetchone()
sys.stderr.write("\n")
for status in statuses:
    print repr(status), statuses[status]
