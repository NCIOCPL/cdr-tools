#----------------------------------------------------------------------
#
# $Id$
#
# Glossary Term and Drug Term Definition Report
#
# "We need a report that lists all glossary terms of the TermType Drug with
# definitions, and finds a corresponding HP Drug Dictionary definition in the
# terminology.  
# Part I:  Use string matching to compare GlossaryTerm with TermType of Drug
# to PreferredName in the terminology for type of Drug/Agent.
#
# Part II:  Use string matching to compare GlossaryTerm with TermType of Drug
# to OtherTermName value with paired OtherNameType value of Synonym or US
# Brand Name in the terminology for terms with SemanticType of Drug/Agent.
# Take out any exact matches (case insensitive). 
#
# I am attaching a sample document to this issue.  I will put in a separate
# issue for the CDR Admin menu information for access to the report.
#
# BZIssue::2010
#
#----------------------------------------------------------------------
import cdrdb, cdr, cdrcgi, xml.dom.minidom, cgi, sys

class GlossaryTerm:
    def __init__(self, docId, termName, node):
        self.docId      = docId
        self.termName   = termName
        self.definition = None
        for child in node.childNodes:
            if child.nodeName == 'TermDefinition':
                for gc in child.childNodes:
                    if gc.nodeName == 'DefinitionText':
                        self.definition = cdr.getTextContent(gc, True)

class Term:
    def __init__(self, docId, termName, node):
        self.docId      = docId
        self.termName   = termName
        self.otherNames = []
        self.definition = None
        for child in node.childNodes:
            if child.nodeName == 'Definition':
                definition = None
                wanted = False
                for gc in child.childNodes:
                    if gc.nodeName == 'DefinitionText':
                        definition = cdr.getTextContent(gc, True)
                    elif gc.nodeName == 'DefinitionType':
                        t = cdr.getTextContent(gc).upper()
                        if t == 'HEALTH PROFESSIONAL':
                            wanted = True
                if definition and wanted:
                    self.definition = definition
            elif child.nodeName == 'OtherName':
                name = None
                wanted = False
                for gc in child.childNodes:
                    if gc.nodeName == 'OtherTermName':
                        name = cdr.getTextContent(gc)
                    elif gc.nodeName == 'OtherNameType':
                        t = cdr.getTextContent(gc).upper()
                        if t in ('SYNONYM', 'US BRAND NAME'):
                            wanted = True
                if name and wanted:
                    self.otherNames.append(name)

def fix(s):
    return s and cgi.escape(s) or u"&nbsp;"

def fixList(values):
    return values and u"<br />".join([fix(v) for v in values]) or u"&nbsp;"

html = [u"""\
<html>
 <head>
  <meta http-equiv='Content-Type' content='text/html; charset=utf-8'>
  <title>Glossary Term and Drug Term Definition Report</title>
  <style type = 'text/css'>
   body { font-family: Arial }
   h1   { font-size: 18 }
  </style>
 </head>
 <body>
  <h1>Glossary Term and Drug Term Definition Report</h1>
  <table border='1' cellpadding='2' cellspacing='0'>
   <tr>
    <th>CDR ID</th>
    <th>Glossary Term</th>
    <th>Definition</th>
    <th>CDR ID</th>
    <th>Drug/Agent PT</th>
    <th>Synonym US Brand Names</th>
    <th>Definition</th>
   </tr>"""]
terms = {}
glossaryTerms = {}
conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
cursor.execute("""\
  SELECT t.doc_id, t.value, g.doc_id, g.value
    FROM query_term t
    JOIN query_term g
      ON t.value = g.value
    JOIN query_term d
      ON d.doc_id = g.doc_id
   WHERE t.path = '/Term/PreferredName'
     AND g.path = '/GlossaryTerm/TermName'
     AND d.path = '/GlossaryTerm/TermType'
     AND d.value = 'Drug'
ORDER BY g.value""")
for termId, termName, glossaryId, glossaryName in cursor.fetchall():
    if termId in terms:
        term = terms[termId]
    else:
        cursor.execute("SELECT xml FROM document WHERE id = ?", termId)
        rows = cursor.fetchall()
        dom = xml.dom.minidom.parseString(rows[0][0].encode('utf-8'))
        term = Term(termId, termName, dom.documentElement)
        terms[termId] = term
    if glossaryId in glossaryTerms:
        glossaryTerm = glossaryTerms[glossaryId]
    else:
        cursor.execute("SELECT xml FROM document WHERE id = ?", glossaryId)
        rows = cursor.fetchall()
        dom = xml.dom.minidom.parseString(rows[0][0].encode('utf-8'))
        node = dom.documentElement
        glossaryTerm = GlossaryTerm(glossaryId, glossaryName, node)
        glossaryTerms[glossaryId] = glossaryTerm
    html.append(u"""\
   <tr>
    <td valign='top'>%d</td>
    <td valign='top'>%s</td>
    <td valign='top'>%s</td>
    <td valign='top'>%d</td>
    <td valign='top'>%s</td>
    <td valign='top'>%s</td>
    <td valign='top'>%s</td>
   </tr>""" % (glossaryTerm.docId, fix(glossaryTerm.termName),
               fix(glossaryTerm.definition), term.docId,
               fix(term.termName), fixList(term.otherNames),
               fix(term.definition)))
html.append(u"""\
  </table>
  <br /><br />
  <table border='1' cellspacing='0' cellpadding='2'>
   <tr>
    <th>CDRID</th>
    <th>Glossary Term</th>
    <th>CDRID</th>
    <th>Drug/Agent PT</th>
   </tr>""")
cursor.execute("""\
  SELECT g.doc_id, g.value, t.doc_id, t.value
    FROM query_term g
    JOIN query_term d
      ON d.doc_id = g.doc_id
    JOIN query_term o
      ON o.value = g.value
    JOIN query_term s
      ON o.doc_id = s.doc_id
     AND LEFT(o.node_loc, 4) = LEFT(s.node_loc, 4)
    JOIN query_term t
      ON t.doc_id = o.doc_id
   WHERE g.path = '/GlossaryTerm/TermName'
     AND d.path = '/GlossaryTerm/TermType'
     AND o.path = '/Term/OtherName/OtherTermName'
     AND s.path = '/Term/OtherName/OtherNameType'
     AND t.path = '/Term/PreferredName'
     AND d.value = 'Drug'
     AND s.value IN ('US brand name', 'Synonym')
     AND t.value <> o.value
ORDER BY t.value""")
for row in cursor.fetchall():
    html.append(u"""\
   <tr>
    <td valign='top'>%d</td>
    <td valign='top'>%s</td>
    <td valign='top'>%d</td>
    <td valign='top'>%s</td>
   </tr>""" % (row[0], fix(row[1]), row[2], fix(row[3])))
html.append("""\
  </table>
 </body>
</html>
""")
cdrcgi.sendPage(u"\n".join(html))
