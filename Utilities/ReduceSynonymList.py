#----------------------------------------------------------------------
#
# $Id$
#
# Olga/Mike:
#
# I have written a post-processor which filters out unwanted forms and
# entries.  The results are in \\\Imbncipf01\public\cdr\Thesaurus.xml.
# I collected and processed each group ("entry") as follows:
#
# * for each form:
#   * strip out commas and apostrophes
#   * extract a set of whitespace-delimited words
#   * normalize the words in the set (uppercase them)
#   * discard stopwords from the set
# * sort the forms, placing forms with more words in the set after
#   forms with fewer words
# * for each form (in order of the sorted list):
#   * if another form later in the list has all of the words in this form's
#     word list:
#     * drop the form
#   * otherwise:
#     * keep the form
# * if two or more forms are kept for the entry:
#   * include the entry in the output document
# * otherwise:
#   * drop the entry from the document
#
# The new document is approximately 2/3 the size of the original.
#
# BZIssue::1728
#
#----------------------------------------------------------------------
import xml.sax.saxutils, sys, xml.dom.minidom, cdr, re

def fix(s):
    return xml.sax.saxutils.escape(s)

def loadStopwords():
    stopwords = {}
    dom = xml.dom.minidom.parse("StopWords.xml")
    for node in dom.documentElement.childNodes:
        if node.nodeName == 'STOP_WORD':
            word = cdr.getTextContent(node).strip()
            if word:
                stopwords[word.upper()] = word
    return stopwords

class ThesaurusForm:

    def __init__(self, node, regex, stopwords):
        self.name = cdr.getTextContent(node).strip()
        self.normalized = self.name.replace(',', '').replace("'", "")
        self.words = {}
        self.keys = []
        for word in regex.split(self.normalized):
            ucWord = word.upper()
            if ucWord not in stopwords:
                self.words[ucWord] = word
                self.keys.append(ucWord)

    def isDuplicate(self, other):
        if len(self.words) > len(other.words):
            return False
        for key in self.keys:
            if key not in other.words:
                return False
        return True

class ThesaurusEntry:

    def __init__(self, node, regex, stopwords):
        self.forms = []
        for child in node.childNodes:
            if child.nodeName == 'THESAURUS_FORM':
                self.forms.append(ThesaurusForm(child, regex, stopwords))

    def reduceForms(self):
        self.forms.sort(lambda a,b: cmp(len(a.words), len(b.words)))
        i = 0
        result = []
        while i < len(self.forms):
            form = self.forms[i]
            wanted = True
            j = i + 1
            while wanted and j < len(self.forms):
                if form.isDuplicate(self.forms[j]):
                    wanted = False
                    break
                j += 1
            if wanted:
                result.append(form)
            i += 1
        return [form.name for form in result]

regex     = re.compile("\\s+")
stopwords = loadStopwords()
nEntries  = 0
dom       = xml.dom.minidom.parse(sys.argv[1])
print "<?xml version='1.0' encoding='utf-8'?>"
print "<THESAURUS>"
for node in dom.documentElement.childNodes:
    if node.nodeName == 'THESAURUS_ENTRY':
        entry = ThesaurusEntry(node, regex, stopwords)
        forms = entry.reduceForms()
        if len(forms) > 1:
            print " <THESAURUS_ENTRY>"
            for form in forms:
                name = fix(form)
                element = u"  <THESAURUS_FORM>%s</THESAURUS_FORM>\n" % name
                sys.stdout.write(element.encode('utf-8'))
            print " </THESAURUS_ENTRY>"
            nEntries += 1
            sys.stderr.write("\r%d entries written" % nEntries)
print "</THESAURUS>"
sys.stderr.write("\n")
