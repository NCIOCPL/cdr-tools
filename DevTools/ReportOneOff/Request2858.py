#----------------------------------------------------------------------
#
# $Id$
#
# Genetics Dictionary
#
# "We would like to create a report from the CDR that could be used to
# generate a Genetics Dictionary on Cancer.gov.  We need a report containing
# all of the glossary terms with Dictionary=Genetics and Audience=HP,
# generated in HTML so that it can go directly on Cancer.gov without
# modification.  I will attach a sample document shortly.  Many of the
# definitions will also include an external link to the NCI Thesaurus record
# for that term."
#
# BZIssue::2858
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
            url = (u"http://nciterms.nci.nih.gov"
                   u"/NCIBrowser/ConceptReport.jsp"
                   u"?dictionary=NCI_Thesaurus"
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
fp = open('Request2858.html', 'w')
fp.write(cdrcgi.unicodeToLatin1(u"".join(html)))
fp.close()
