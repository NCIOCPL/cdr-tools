#----------------------------------------------------------------------
#
# $Id$
#
# Find trials with "DUP" as substring in selected comment fields.
#
# BZIssue::4824
#
#----------------------------------------------------------------------
import lxml.etree, cdrdb, cgi, sys

def fix(me):
    if not me:
        return ''
    return cgi.escape(me).encode('utf-8')

cursor = cdrdb.connect('CdrGuest', dataSource='bach.nci.nih.gov').cursor()
cursor.execute("""\
    SELECT DISTINCT n.doc_id, n.value
               FROM query_term n
               JOIN query_term t
                 ON t.doc_id = n.doc_id
                AND LEFT(t.node_loc, 4) = LEFT(n.node_loc, 4)
              WHERE t.value = 'ClinicalTrials.gov ID'
                AND t.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
                AND n.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDString'
                AND n.value LIKE 'NCT%'
           ORDER BY 1""", timeout=300)
rows = cursor.fetchall()
print """\
<html>
 <table style='font-family: Arial;' border='1' cellpadding='2' cellspacing='0'>
  <tr style='color: green'>
   <th>CDR ID</th>
   <th>NLM ID</th>
   <th>Duplicate Comment</th>
  </tr>"""
for i, row in enumerate(rows):
    cdrId, nlmId = row
    cursor.execute("SELECT xml FROM document WHERE id = ?", cdrId)
    try:
        docXml = cursor.fetchall()[0][0]
        tree = lxml.etree.XML(docXml.encode('utf-8'))
        comments = []
        for node in tree.findall('ProtocolIDs/PrimaryID/Comment'):
            comments.append(node.text)
        for node in tree.findall('ProtocolIDs/OtherID/Comment'):
            comments.append(node.text)
        for comment in comments:
            if 'DUP' in comment.upper():
                print u"""\
  <tr>
   <td>%d</td>
   <td>%s</td>
   <td>%s</td>
  </tr>""" % (cdrId, fix(nlmId), fix(comment))
    except Exception, e:
        print (u"""\
  <tr style='color: red'>
   <td>%d</td>
   <td>%s</td>
   <td>%s</td>
  </tr>""" % (cdrId, nlmId,
              u"FAILURE: %s" % cgi.escape(unicode(e)))).encode('utf-8')
    sys.stderr.write("\rprocessed %d of %d documents" % (i + 1, len(rows)))
print """\
 </table>
</html>"""
