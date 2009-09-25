#----------------------------------------------------------------------
#
# $Id: Request4609.py,v 1.1 2009-09-25 19:09:49 venglisc Exp $
#
# Create a report with an updated NCI Thesaurus link.
# (This report is based on Bob's Request2858)
#
# $Log: not supported by cvs2svn $
#
#----------------------------------------------------------------------
import ExcelReader, cdrcgi, cgi

class Term:
    def __init__(self, termName, termDef, conceptId):
        self.termName  = termName
        self.upperName = termName.upper()
        self.termDef   = termDef
        self.conceptId = conceptId
    def __cmp__(self, other):
        return cmp(self.upperName, other.upperName)
    def toHtml(self):
        html = [u"""\
  <p class='term'><span class='term-name'>%s</span><br />%s"""
                % (cgi.escape(self.termName), cgi.escape(self.termDef))]
        if self.conceptId:
            url = (u"http://ncit.nci.nih.gov"
                   u"/ncitbrowser/ConceptReport.jsp"
                   u"?dictionary=NCI%%20Thesaurus"
                   u"&code=%s" % self.conceptId)
            html.append(u" (<a href='%s'>NCI Thesaurus</a>)" % url)
        html.append(u"</p>\n")
        return u"".join(html)

#book = ExcelReader.Workbook('Genetics Dictionary.xls')
#book = ExcelReader.Workbook('Request2858.xls')
book = ExcelReader.Workbook('GeneticsDictionary030607.xls')
sheet = book[0]
alphabet = {}
html = [u"""\
  <style type='text/css'>
   body { font-family: Arial }
   .letter { font-weight: bold; text-decoration: underline; color: blue; }
   .term-name { font-weight: bold; }
  </style>
"""]
for row in sheet:
    if row.number > 0:
        termName = row[3].val
        try:
            termDef = row[5].val
        except:
            termDef = u""
        try:
            conceptId = row[1].val
        except:
            conceptId = None
        term = Term(termName, termDef, conceptId)
        letter = termName[0].upper()
        if letter in alphabet:
            alphabet[letter].append(term)
        else:
            alphabet[letter] = [term]
letters = alphabet.keys()
letters.sort()
for letter in letters:
    html.append(u"""\
  <p class='letter'><a name='letter-%s'>%s</a></p>
""" % (letter, letter))
    subset = alphabet[letter]
    subset.sort()
    for term in subset:
        html.append(term.toHtml())
fp = open('Request4609.html', 'w')
fp.write(cdrcgi.unicodeToLatin1(u"".join(html)))
fp.close()
