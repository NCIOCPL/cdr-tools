#----------------------------------------------------------------------
#
# $Id$
#
# Export CDR document XML for translation in World Server.
#
# JIRA::OCECDR-3783 - drop Comment elements
#
#----------------------------------------------------------------------
import cdrdb
import sys
import lxml.etree as etree

#----------------------------------------------------------------------
# Check command-line arguments.
#----------------------------------------------------------------------
try:
    doc_id = int(sys.argv[1])
    version = len(sys.argv) > 2 and int(sys.argv[2]) or None
except:
    sys.stderr.write("usage: FetchDocForTranslation.py doc-id [doc-version]\n")
    sys.exit(1)

#----------------------------------------------------------------------
# Fetch the document's XML.
#----------------------------------------------------------------------
if version:
    query = cdrdb.Query("doc_version", "xml")
    query.where("id = %d" % doc_id)
    query.where("num = %d" % version)
else:
    query = cdrdb.Query("document", "xml")
    query.where("id = %d" % doc_id)
try:
    doc_xml = query.execute().fetchall()[0][0]
except:
    sys.stderr.write("document not found\n")
    sys.exit(1)

#----------------------------------------------------------------------
# Process the document.
#----------------------------------------------------------------------
tree = etree.fromstring(doc_xml.encode("utf-8"))
for comment in tree.xpath("//Comment"):
  comment.getparent().remove(comment)

#----------------------------------------------------------------------
# Send the results to standard output.
#----------------------------------------------------------------------
print etree.tostring(tree, xml_declaration=True)
