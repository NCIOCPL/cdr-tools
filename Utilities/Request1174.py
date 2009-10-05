#----------------------------------------------------------------------
#
# $Id: Request1174.py,v 1.2 2004-06-19 12:30:02 bkline Exp $
#
# Report on Board member CIPS contact addresses (one-off for Lakshmi).
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2004/04/05 19:32:33  bkline
# One-off report on Board member CIPS contact addresses for Lakshmi.
#
#----------------------------------------------------------------------
import cdr, cdrdb, cdrcgi, re, sys, xml.sax.saxutils, xml.dom.minidom

def extractAddress(xmlContent):
    lines = u''
    sep = u''
    dom = xml.dom.minidom.parseString(xmlContent)
    for node in dom.documentElement.childNodes:
        if node.nodeName == 'OrgName':
            lines += sep + xml.sax.saxutils.escape(cdr.getTextContent(node))
            sep = u'<br>'
        elif node.nodeName == 'ParentNames':
            for child in node.childNodes:
                if child.nodeName == 'ParentName':
                    value = xml.sax.saxutils.escape(cdr.getTextContent(child))
                    lines += sep + value
                    sep = u'<br>'
        elif node.nodeName == 'PostalAddress':
            for child in node.childNodes:
                if child.nodeName in ('Street','City','State','Country',
                                      'PostalCode_ZIP'):
                    value = xml.sax.saxutils.escape(cdr.getTextContent(child))
                    lines += sep + value
                    sep = u'<br>'
    return lines
                
conn = cdrdb.connect("CdrGuest")
cursor = conn.cursor()
paths = ("/Person/ProfessionalInformation/PDQBoardMembershipDetails"
         "/PDQAdvisoryBoard/@cdr:ref",
         "/Person/ProfessionalInformation/PDQBoardMembershipDetails"
         "/PDQEditorialBoard/@cdr:ref")
cursor.execute("""\
    SELECT DISTINCT q.doc_id, b.id, b.title, p.title, f.value
      FROM query_term q
      JOIN document p
        ON q.doc_id = p.id
      JOIN document b
        ON q.int_val = b.id
      JOIN query_term f
        ON f.doc_id = p.id
     WHERE q.path IN (?, ?)
       AND f.path = '/Person/PersonLocations/CIPSContact'
  ORDER BY b.title, p.title""", paths)
lastBoard = None
filters = ['name:Person Address Fragment With Name']
report = u"""\
<html>
 <head>
  <meta content="text/html;charset=utf-8" http-equiv="Content-Type">
  <title>CIPS Contact Info for PDQ Editorial and Advisory Board Members</title>
  <style type='text/css'>
   body { font-family: Arial }
  </style>
 </head>
 <body>
  <h1>CIPS Contact Info for PDQ Editorial and Advisory Board Members</h1>
  <br>
  <table border='0' cellspacing='0' cellpadding='3'>
"""
for personId, boardId, boardTitle, personName, fragId in cursor.fetchall():
    #sys.stderr.write("person %d\n" % personId)
    parms = (('fragId', fragId),)
    response = cdr.filterDoc('guest', filters, personId, parm = parms)
    if type(response) in (type(""), type(u"")):
        cdrcgi.bail("ERROR: %s\n" % response)
    else:
        if boardId != lastBoard:
            semicolon = boardTitle.find(';')
            if semicolon != -1:
                boardTitle = boardTitle[:semicolon]
            report += """\
   <tr>
    <td colspan='3'><b>%s (CDR%d) </b></td>
   </tr>
   <tr><td colspan='3'>&nbsp;</td></tr>
""" % (xml.sax.saxutils.escape(boardTitle), boardId)
            lastBoard = boardId
        semicolon = personName.find(';')
        if semicolon:
            personName = personName[:semicolon]
        report += u"""\
   <tr>
    <td>&nbsp;&nbsp;&nbsp;</td>
    <td valign='top'>%s (CDR%d)</td>
    <td valign='top'>%s</td>
   </tr>
   <tr><td colspan='3'>&nbsp;</td></tr>
""" % (xml.sax.saxutils.escape(personName), personId,
       extractAddress(response[0]))
report += """\
  </table>
 </body>
</html>
"""
#sys.stdout.write(report.encode('utf-8'))
cdrcgi.sendPage(report)
