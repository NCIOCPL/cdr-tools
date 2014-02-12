#----------------------------------------------------------------------
#
# $Id$
#
# "For all concepts that have <kind>Findings_And_Disorders_Kind</kind> OR
# <kind>Chemicals_And_Drugs_Kind</kind>, grab all the <term-name> values
# from <property> nodes that have <name>Full_syn</name> and <term_source>NCI
# or NCI_GLOSS.
#
# "Since Bob is familiar with the NCI thesaurus, we thought this would be a
# quick way to get Cancer.gov the data that is needed for query term
# expansion."
#
# BZIssue::1728
#
#----------------------------------------------------------------------
import PdqThesaurus, xml.sax.handler, sys, xml.dom.minidom, cdr, re

def loadStopwords():
    stopwords = {}
    dom = xml.dom.minidom.parse("StopWords.xml")
    for node in dom.documentElement.childNodes:
        if node.nodeName == 'STOP_WORD':
            word = cdr.getTextContent(node).strip()
            if word:
                stopwords[word.upper()] = word
    return stopwords

def fix(s):
    return s.encode('utf-8')

def addName(names, name):
    name = name.strip()
    key  = name.upper()
    if key not in names:
        names[key] = name

def addNames(preferredName, concepts, names):
    key = preferredName.strip().upper()
    if key in concepts:
        logFile.write("multiple concepts for %s\n" % fix(preferredName))
        oldNames = concepts[key]
        for name in names:
            if name not in oldNames:
                oldNames[name] = names[name]
    else:
        concepts[key] = names

class Name:
    def __init__(self, name, regex, stopwords):
        self.name = name
        self.normalized = name.replace(',', '').replace("'", "")
        self.words = {}
        self.keys = []
        for word in regex.split(self.normalized):
            ucWord = word.upper()
            if ucWord not in stopwords:
                self.words[ucWord] = word
                self.keys.append(ucWord)

def isDuplicate(name1, name2):
    if len(name1.words) < len(name2.words):
        return False
    for key in name1.keys:
        if key not in name2.words:
            return False
    return True

def reduceNames(names, regex, stopwords):
    nameList = []
    for name in names:
        nameList.append(Name(name, regex, stopwords))
    i = 0
    result = []
    while i < len(nameList):
        n = nameList[i]
        wanted = True
        j = i + 1
        while wanted and j < len(nameList):
            if isDuplicate(n, nameList[j]):
                wanted = False
                break
            j += 1
        if wanted:
            result.append(n)
        i += 1
    return [n.name for n in result]

regex     = re.compile("\\s+")
stopwords = loadStopwords()
logFile   = open('Request1728.log', 'w')
nConcepts = 0
nNames    = 0
concepts  = {}
print "<?xml version='1.0' encoding='utf-8'?>"
print "<THESAURUS>"
thesaurus = PdqThesaurus.Thesaurus()
xml.sax.parse(sys.argv[1], thesaurus)
sys.stderr.write("\n")
for code in thesaurus.terms:
    concept = thesaurus.terms[code]
    if concept.kind in ('Findings_and_Disorders_Kind',
                        'Chemicals_and_Drugs_Kind'):
        names = {}
        addName(names, concept.preferredName)
        for syn in concept.fullSyn:
            if syn.termSource in ('NCI', 'NCI_GLOSS'):
                addName(names, syn.termName)
        addNames(concept.preferredName, concepts, names)
    nConcepts += 1
    nNames += len(names)
    sys.stderr.write("\r%d names found in %d concepts" % (nNames, nConcepts))
for preferredTerm in concepts:
    names = concepts[preferredTerm]
    names = reduceNames(names, regex, stopwords)
    if len(names) > 1:
        print " <THESAURUS_ENTRY>"
        for names in names:
            element = u"  <THESAURUS_FORM>%s</THESAURUS_FORM>\n" % name
            sys.stdout.write(element.encode('utf-8'))
        print " </THESAURUS_ENTRY>"
print "</THESAURUS>"
sys.stderr.write("\n")
