#----------------------------------------------------------------------
#
# $Id$
#
# Issue 3723:
# We need the data in the current Glossary document to be converted for the
# new data structure which separates Term Names and definitions into two
# separate documents: GlossaryTermName and GlossaryTermConcept.
#
# Information about the data conversion has been discussed in issue 3120.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2008/08/25 16:00:30  bkline
# Program to create GlossaryTermConcept and GlossaryTermName documents
# from the GlossaryTerm documents.
#
#----------------------------------------------------------------------
import cdr, cdrdb, xml.dom.minidom, cPickle, sys, getopt, time, difflib, re, os
import cgi

LOGFILE = cdr.DEFAULT_LOGDIR + "/ConvertGlossaryDocs.log"
MIN_MATCH = 4
DEF_KEYS = ("EP", "EH", "SP", "SH")
PH_NAME = u"<PlaceHolder name='TERMNAME'/>"
PH_CAPPEDNAME = u". <PlaceHolder name='CAPPEDTERMNAME'/>"
DEBUGGING = False

def stripFragmentIds(docXml):
    xsltFilter = """\
<?xml version='1.0' encoding='UTF-8'?>

<xsl:transform                version = '1.0' 
                            xmlns:xsl = 'http://www.w3.org/1999/XSL/Transform'
                            xmlns:cdr = 'cips.nci.nih.gov/cdr'>

 <xsl:output                   method = 'xml'/>

 <!--
 =======================================================================
 Copy most things straight through.
 ======================================================================= -->
 <xsl:template                  match = '@*|node()|comment()|
                                         processing-instruction()'>
  <xsl:copy>
   <xsl:apply-templates        select = '@*|node()|comment()|
                                         processing-instruction()'/>
  </xsl:copy>
 </xsl:template>

 <!-- These we don't want. -->
 <xsl:template                  match = '@cdr:id'/>

</xsl:transform>
"""
    result  = cdr.filterDoc('guest', xsltFilter, doc = docXml, inline = True)
    if type(result) in (str, unicode):
        raise Exception(result)
    return result[0]

def fix(me):
    if not me:
        return u""
    return cgi.escape(me)

def stringsDiffer(strings):
    if len(strings) < 2:
        return False
    i = 1
    while i < len(strings):
        if strings[i] != strings[i - 1]:
            return True
        i += 1
    return False

# Make sure we haven't created a malformed segment in our split.
def malformedLists(wordLists):
    for wordList in wordLists:
        # was u"".join() - that's a mistake, right?
        if malformed(u" ".join(wordList)):
            return True
    return False

def malformed(s):
    test = (u"<x xmlns:cdr='cips.nci.nih.gov/cdr'>%s</x>" % s).encode('utf-8')
    try:
        xml.dom.minidom.parseString(test)
    except Exception, e:
        sys.stderr.write("failed: '%s': %s\n" % (test, e))
        return True
    return False

class CommonWords:
    def __init__(self, wordLists):

        # Sanity check.
        if len(wordLists) < 2 or type(wordLists) not in (tuple, list):
            raise Exception("findCommonChunk(): "
                            "sequence of word lists expected")

        # Start with the assumption that no good match is found.
        self.prefixes = wordLists
        self.common   = None
        self.suffixes = None

        # Compare the first two word sequences.
        sm = difflib.SequenceMatcher()
        sm.set_seqs(wordLists[0], wordLists[1])
        start1, start2, length = sm.find_longest_match(0, len(wordLists[0]),
                                                       0, len(wordLists[1]))

        # If the match isn't long enough, behave as if there's no match.
        if DEBUGGING:
            print "length of match is %d" % length
        if length < MIN_MATCH:
            return

        # Provisional values for the object's attributes.
        common   = wordLists[0][start1:start1 + length]
        prefixes = [wordLists[0][:start1], wordLists[1][:start2]]
        suffixes = [wordLists[0][start1 + length:], 
                    wordLists[1][start2 + length:]]
        if DEBUGGING:
            print "common: %s" % common
        
        # See how well the other word sequences contain our common segment.
        i = 2
        while i < len(wordLists):
            sm.set_seqs(common, wordLists[i])
            start1, start2, length = sm.find_longest_match(0, len(common),
                                                           0, len(wordLists[i]))

            # Bail if at any time our common sequence shrinks too far.
            if DEBUGGING:
                "now length of match is %d" % length
            if length < MIN_MATCH:
                return

            # If the common sequence shrank, adjust what we have so far.
            if length < len(common):
                diffAtFront = common[:start1]
                diffAtBack  = common[start1 + length:]
                for j in range(i):
                    prefixes[j] += diffAtFront
                    suffixes[j] = diffAtBack + suffixes[j]
                common = common[start1:start1 + length]

            # Add the prefixes and suffixes from this sequence.
            prefixes.append(wordLists[i][:start2])
            suffixes.append(wordLists[i][start2 + length:])

            # Move to the next sequence.
            i += 1

        # See if we have any prefix or suffix strings.
        self.prefixes = None
        self.suffixes = None
        emptyPrefix = havePrefix = False
        for prefix in prefixes:
            if prefix:
                havePrefix = True
            else:
                emptyPrefix = True
        if havePrefix:
            if malformedLists(prefixes):
                return
            if emptyPrefix:
                for prefix in prefixes:
                    prefix.append(common[0])
                common = common[1:]
            self.prefixes = prefixes
        emptySuffix = haveSuffix = False
        for suffix in suffixes:
            if suffix:
                haveSuffix = True
            else:
                emptySuffix = True
        if haveSuffix:
            if malformedLists(suffixes):
                return
            if emptySuffix:
                for suffix in suffixes:
                    suffix.insert(0, common[-1])
                common = common[:-1]
            self.suffixes = suffixes

        # Remember what we came looking for.
        if len(common) < MIN_MATCH or malformedLists([common]):
            return
        self.common = common

def buildChain(wordLists):
    if not wordLists:
        return []
    cw = CommonWords(wordLists)
    if not cw.common:
        return [wordLists]
    return buildChain(cw.prefixes) + cw.common + buildChain(cw.suffixes)

def mergeDefs(defs):
    if not defs:
        raise Exception("mergeDefs(): no definitions supplied")
    if len(defs) == 1:
        return defs
    wordLists = [re.sub(u'\\s+', u' ', d).split() for d in defs]
    return buildChain(wordLists)

class Opts:
    def __init__(self):
        self.fileName  = ""
        self.mode      = None
        self.maxGroups = 1
        self.user      = ""
        self.password  = ""
        try:
            longopts = ["testmode", "livemode", "maxgroups=", "groupfile=",
                        "user=", "password="]
            opts, args = getopt.getopt(sys.argv[1:], "tlg:m:u:p:", longopts)
        except getopt.GetoptError, e:
            Opts.usage()
        for o, a in opts:
            if o in ("-t", "--testmode"):
                self.mode = "TEST"
            elif o in ("-l", "--livemode"):
                self.mode = "LIVE"
            elif o in ("-m", "--maxgroups"):
                try:
                    self.maxGroups = int(a)
                except Exception, e:
                    sys.stderr.write("whoops! %s" % e)
                    Opts.usage()
            elif o in ("-g", "--groupfile"):
                self.fileName = a
                sys.stderr.write("using group file %s\n" % a)
            elif o in ("-u", "--user"):
                self.user = a
            elif o in ("-p", "--password"):
                self.password = a
            else:
                Opts.usage()
        if not self.mode or self.maxGroups is None:
            Opts.usage()
        if self.mode == "LIVE" and not (self.user and self.password):
            Opts.usage()
        sys.stderr.write("Running in %s mode\n" % self.mode)
        sys.stderr.write("Will process at most %d groups\n" % self.maxGroups)
    @staticmethod
    def usage():
        sys.stderr.write("""\
usage: %s [options]

options:
    -t                 run in test mode
    -l                 run in live mode
    -u name            run as user `name'
    -p pw              run using password `pw'
    -m N               maximum number of groups to process for this run
    -g name            file listing groups
    --groupfile=name   file listing groups
    --maxgroups=N      maximum number of groups to process for this run
    --testmode         run in test mode
    --livemode         run in live mode
    --user=name        run as user `name'
    --password=pw      run using password `password'

    Invocation must specify mode and the number of groups to process
    If group filename is omitted, groups will be freshly determined
    If running in live mode, user and password are required
""" % sys.argv[0])
        sys.exit(1)

class GlossaryTerm:
    @staticmethod
    def mapStatus(s):
        return {
            'Pending'                     : 'New pending',
            'Translation approved'        : 'Approved',
            'Translation pending'         : 'New pending',
            'Translation revision pending': 'Revision pending'
        }.get(s, s)

    def makeNameDoc(self, concept):
        docXml = [u"""\
<?xml version='1.0' encoding='utf-8'?>
<GlossaryTermName xmlns:cdr='cips.nci.nih.gov/cdr'>
"""]
        if self.englishTermName:
            docXml.append(u"""\
 <TermName>
  <TermNameString>%s</TermNameString>
""" % fix(self.englishTermName))
            if self.pron:
                docXml.append(u"""\
  <TermPronunciation>%s</TermPronunciation>
""" % fix(self.pron))
            for pronRes in self.pronRes:
                docXml.append(u"""\
  <PronunciationResource>%s</PronunciationResource>
""" % fix(pronRes))
            if self.source:
                docXml.append(u"""\
  <TermNameSource>%s</TermNameSource>
""" % fix(self.source))
            docXml.append(u"""\
 </TermName>
""")
        if self.termStatus:
            docXml.append(u"""\
 <TermNameStatus>%s</TermNameStatus>
""" % GlossaryTerm.mapStatus(self.termStatus))
        if self.statusDate:
            docXml.append(u"""\
 <TermNameStatusDate>%s</TermNameStatusDate>
""" % self.statusDate)
        if self.spanishTermName:
            docXml.append(u"""\
 <TranslatedName language='es'>
  <TermNameString>%s</TermNameString>
  <TranslatedNameStatus>Approved</TranslatedNameStatus>
""" % fix(self.spanishTermName))
            docXml.append(u"""\
 </TranslatedName>
""")
        docXml.append(u"""\
 <GlossaryTermConcept cdr:ref='CDR%010d'/>
""" % concept.docId)
        for r in self.replacements:
            docXml.append(u"""\
 %s
""" % r)
        for c in self.comments:
            docXml.append(u"""\
 %s
""" % c)
        docXml.append(u"""\
</GlossaryTermName>
""")
        return u"".join(docXml)

    def __init__(self, docId, cursor):
        cdr.logwrite("converting CDR%d" % docId, LOGFILE)
        versions             = cdr.lastVersions('guest', "CDR%010d" % docId)
        self.lastVersion     = versions[0] != -1 and versions[0] or None
        self.lastPubVersion  = versions[1] != -1 and versions[1] or None
        self.changed         = versions[2] == 'Y'
        self.version         = self.lastPubVersion or self.lastVersion
        self.docId           = docId
        self.activeStatus    = cdr.getDocStatus('guest', docId)
        self.blocked         = self.activeStatus != 'A'
        self.hasMarkup       = False
        self.englishTermName = None
        self.thesId          = None
        self.pron            = None
        self.pronRes         = []
        self.englishDefs     = []
        self.media           = []
        self.spanishTermName = None
        self.spanishDefs     = []
        self.source          = None
        self.types           = []
        self.termStatus      = None
        self.statusDate      = None
        self.comments        = []
        self.lastMod         = None
        self.lastReviewed    = None
        self.pdqKey          = None
        self.replacements    = []
        if self.version:
            cursor.execute("""\
                SELECT xml
                  FROM doc_version
                 WHERE id = ?
                   AND num = ?""", (docId, self.version))
        else:
            cursor.execute("""\
                SELECT xml
                  FROM document
                 WHERE id = ?""", docId)
        docXml = stripFragmentIds(cursor.fetchall()[0][0].encode('utf-8'))
        dom = xml.dom.minidom.parseString(docXml)
        for node in dom.documentElement.childNodes:
            if node.nodeName == 'TermName':
                if self.englishTermName:
                    raise Exception("multiple term names")
                self.englishTermName = cdr.getTextContent(node)
            elif node.nodeName == 'NCIThesaurusConceptID':
                if self.thesId:
                    raise Exception("multiple thesaurus IDs")
                self.thesId = cdr.getTextContent(node)
            elif node.nodeName == 'TermPronunciation':
                if self.pron:
                    raise Exception("multiple term pronunciations")
                pron = cdr.getTextContent(node).strip()
                if pron and pron[0] == '(' and pron[-1] == ')':
                    pron = pron[1:-1]
                if pron:
                    self.pron = pron
            elif node.nodeName == 'PronunciationResource':
                self.pronRes.append(cdr.getTextContent(node))
            elif node.nodeName == 'TermDefinition':
                d = Definition(self, node, 'english')
                if d.hasMarkup:
                    self.hasMarkup = True
                self.englishDefs.append(d)
            elif node.nodeName == 'MediaLink':
                self.media.append(node.toxml())
            elif node.nodeName == 'SpanishTermName':
                if self.spanishTermName:
                    raise Exception("multiple Spanish names")
                self.spanishTermName = cdr.getTextContent(node)
            elif node.nodeName == 'SpanishTermDefinition':
                d = Definition(self, node, 'spanish')
                if d.hasMarkup:
                    self.hasMarkup = True
                self.spanishDefs.append(d)
            elif node.nodeName == 'TermSource':
                if self.source:
                    raise Exception("multiple term sources")
                self.source = cdr.getTextContent(node)
            elif node.nodeName == 'TermType':
                self.types.append(cdr.getTextContent(node))
            elif node.nodeName == 'TermStatus':
                if self.termStatus:
                    raise Exception("multiple term statuses")
                self.termStatus = cdr.getTextContent(node)
            elif node.nodeName == 'StatusDate':
                if self.statusDate:
                    raise Exception("multiple term status dates")
                self.statusDate = cdr.getTextContent(node)
            elif node.nodeName == 'Comment':
                self.comments.append(node.toxml())
            elif node.nodeName == 'DateLastModified':
                if self.lastMod:
                    raise Exception("multiple last modified dates")
                self.lastMod = cdr.getTextContent(node)
            elif node.nodeName == 'DateLastReviewed':
                if self.lastReviewed:
                    raise Exception("multiple last reviewed dates")
                self.lastReviewed = cdr.getTextContent(node)
            elif node.nodeName == 'PdqKey':
                if self.pdqKey:
                    raise Exception("multiple PDQ keys")
                self.pdqKey = cdr.getTextContent(node)
            elif node.nodeType == node.ELEMENT_NODE:
                raise Exception("unexpected element %s" % node.nodeName)
        
class Definition:
    whitespace = re.compile(u"\\s+")
    def __init__(self, term, node, language):
        self.term       = term
        self.language   = language
        self.textXml    = None
        self.hasMarkup  = None
        self.resources  = []
        self.media      = []
        self.dicts      = []
        self.audiences  = set()
        self.status     = None
        self.comments   = []
        self.statusDate = None
        self.lastMod    = None
        for child in node.childNodes:
            if child.nodeName == 'DefinitionText':
                if self.textXml:
                    raise Exception("multiple texts for definition")
                nodes = []
                self.hasMarkup = False
                for grandchild in child.childNodes:
                    nodeName = grandchild.nodeName
                    if nodeName in ('Insertion', 'Deletion'):
                        self.hasMarkup = True
                    nodes.append(grandchild.toxml())
                self.textXml = u"".join(nodes)
            elif child.nodeName == 'DefinitionResource':
                self.resources.append(cdr.getTextContent(child).strip())
            elif child.nodeName == 'MediaLink':
                self.media.append(child.toxml())
            elif child.nodeName == 'Dictionary':
                self.dicts.append(cdr.getTextContent(child))
            elif child.nodeName == 'Audience':
                audience = cdr.getTextContent(child).strip().upper()
                if audience:
                    self.audiences.add(audience[0])
            elif child.nodeName == 'DefinitionStatus':
                if self.status:
                    raise Exception("multiple definition statuses")
                status = cdr.getTextContent(child).strip()
                if status.upper() in (u'TRANSLATION PENDING',
                                      u'TRANSLATION REVISION PENDING'):
                    status = 'Translation approved'
                self.status = status
            elif child.nodeName == 'TranslationResource':
                self.resources.append(cdr.getTextContent(child).strip())
            elif child.nodeName == 'Comment':
                self.comments.append(child.toxml())
            elif child.nodeName == 'StatusDate':
                if self.statusDate:
                    raise Exception("multiple definition status dates")
                self.statusDate = cdr.getTextContent(child)
            elif child.nodeName == 'DateLastModified':
                lastMod = cdr.getTextContent(child)
                if lastMod > self.lastMod:
                    self.lastMod = lastMod
    def normalizeDef(self, names):
        if self.language == 'english':
            alsoCalled = u"also called"
        else:
            alsoCalled = u"tambi\xe9n se llama"
        d = Definition.whitespace.sub(u" ", self.textXml.strip())
        alsoCalled = d.lower().find(alsoCalled)
        if alsoCalled != -1:
            test = d[:alsoCalled].strip()
            if not malformed(test):
                d = test
        for name in names:
            if name:
                name = name[0].upper() + name[1:] + u'. '
                if d.startswith(name):
                    d = d[len(name):].strip()
                    break
        return d

def keepGroup(group, cursor):
    for docId in group:
        cursor.execute("""\
            SELECT t.name
              FROM doc_type t
              JOIN document d
                ON t.id = d.doc_type
             WHERE d.id = ?""", docId)
        rows = cursor.fetchall()
        if not rows:
            sys.stderr.write("dropping group %s; can't get doc type for %s\n" %
                             (group, docId))
            return False
        elif rows[0][0] != 'GlossaryTerm':
            sys.stderr.write("dropping group %s; %s is a %s document\n" %
                             (group, docId, rows[0][0]))
            return False
    return True

def getGroups(cursor, fileName = None):
    groups = []
    if fileName:
        for line in open(fileName):
            docIds = tuple([int(i) for i in line.strip().split()])
            groups.append(docIds)
    else:
        import GlossaryTermGroups
        groups = GlossaryTermGroups.Group.makeGroups(cursor)
    return [group for group in groups if keepGroup(group, cursor)]

class MergedDefinition:
    def toXml(self):
        if not self.text:
            return u""
        if self.language == 'E':
            dtag = u'TermDefinition'
            rtag = u'DefinitionResource'
            attr = u''
        else:
            dtag = u'TranslatedTermDefinition'
            rtag = u'TranslationResource'
            attr = u" language='es'"
        xmlText = [u"<%s%s><DefinitionText>%s</DefinitionText>" % (dtag, attr,
                                                                   self.text)]
        for r in self.resources:
            xmlText.append(u"<%s>%s</%s>" % (rtag, fix(r), rtag))
        for m in self.mediaLinks:
            xmlText.append(m)
        for d in self.dictionaries:
            xmlText.append(u"<Dictionary>%s</Dictionary>" % d)
        xmlText.append(u"<Audience>%s</Audience>" %
                       (self.audience == 'H' and u"Health professional" or
                        u"Patient"))
        if self.status:
            tagFront = self.language == 'E' and "Definition" or "Translated"
            status = GlossaryTerm.mapStatus(self.status)
            xmlText.append(u"<%sStatus>%s</%sStatus>" %
                           (tagFront, status, tagFront))
        for c in self.comments:
            xmlText.append(c)
        if self.lastMod:
            xmlText.append(u"<DateLastModified>%s</DateLastModified>" %
                           self.lastMod)
        if self.lastReviewed:
            xmlText.append(u"<DateLastReviewed>%s</DateLastReviewed>" %
                           self.lastReviewed)
        xmlText.append(u"</%s>" % dtag)
        return u"".join(xmlText)
    def __init__(self, terms, language, audience, lastMod, lastReviewed):
        self.text         = u""
        self.key          = language + audience
        self.resources    = set()
        self.mediaLinks   = set()
        self.dictionaries = set()
        self.audience     = audience
        self.language     = language
        self.status       = u""
        self.statusDate   = self.key == 'EH' and 'Approved' or u''
        self.comments     = set()
        self.lastMod      = language == 'E' and lastMod or u""
        self.lastReviewed = language == 'E' and lastReviewed or u""
        names             = []
        definitions       = []
        for term in terms:
            if language == 'E':
                if term.statusDate > self.statusDate:
                    self.statusDate = term.statusDate
                if audience == 'P':
                    if term.termStatus:
                        if self.status and self.status != term.termStatus:
                            raise Exception("concept group has multiple "
                                            "term status values: %s and %s" %
                                            (self.status, term.termStatus))
                        self.status = term.termStatus
                if term.englishTermName:
                    names.append(term.englishTermName)
                for d in term.englishDefs:
                    if audience in d.audiences:
                        definitions.append(d)
                        break
            else:
                if term.spanishTermName:
                    names.append(term.spanishTermName)
                for d in term.spanishDefs:
                    if audience in d.audiences:
                        definitions.append(d)
                        break
        for definition in definitions:
            for resource in definition.resources:
                self.resources.add(resource)
            for media in definition.media:
                self.mediaLinks.add(media)
            for dictionary in definition.dicts:
                self.dictionaries.add(dictionary)
            for comment in definition.comments:
                self.comments.add(comment)
            if language == 'S':
                if definition.lastMod > self.lastMod:
                    self.lastMod = definition.lastMod
                if definition.status:
                    if self.status and self.status != definition.status:
                        raise Exception("Spanish %s definitions in group "
                                        "have multiple status values: "
                                        "%s and %s\n" % (audience, self.status,
                                                         definition.status))
                    self.status = definition.status
                if definition.statusDate > self.statusDate:
                    self.statusDate = definition.statusDate
        self.text = MergedDefinition.mergeText(definitions, names, self.key)
    @staticmethod
    def mergeText(definitions, names, key):
        if not definitions:
            return None
        normalizedDefs = [d.normalizeDef(names) for d in definitions]
        if not stringsDiffer(definitions):
            return normalizedDefs[0]
        withStockPlaceholders = []
        for i in range(len(normalizedDefs)):
            name = names[i]
            d = normalizedDefs[i]
            if name:
                if len(name) > 1:
                    cappedName = u". " + name[0].upper() + name[1:]
                else:
                    cappedName = u". " + name.upper()
                d = d.replace(cappedName, PH_CAPPEDNAME)
                d = d.replace(name, PH_NAME)
            withStockPlaceholders.append(d)
        if not stringsDiffer(withStockPlaceholders):
            return withStockPlaceholders[0]
        chain = mergeDefs(normalizedDefs)
        base = []
        phId = 1
        for link in chain:
            if type(link) is unicode:
                base.append(link)
            else:
                name = u"%s%d" % (key, phId)
                phId += 1
                base.append(u"<PlaceHolder name='%s'/>" % name)
                for i in range(len(definitions)):
                    t = definitions[i].term
                    r = u" ".join(link[i])
                    t.replacements.append(u"<ReplacementText name='%s'>%s"
                                          u"</ReplacementText>" % (name, r))
        return u" ".join(base)

class GlossaryTermConcept:
    def __init__(self, docIds, cursor):
        self.prefDoc      = None
        self.terms        = [GlossaryTerm(docId, cursor) for docId in docIds]
        self.lastMod      = u""
        self.lastReviewed = u""
        for term in self.terms:
            if term.lastMod > self.lastMod:
                self.lastMod = term.lastMod
            if term.lastReviewed > self.lastReviewed:
                self.lastReviewed = term.lastReviewed
            if term.docId in preferredGlossaryDefinitions:
                if self.prefDoc:
                    raise Exception("multiple docs in group on preferred list")
                self.prefDoc = term
        if not self.prefDoc:
            for term in self.terms:
                if term.hasMarkup:
                    if self.prefDoc:
                        raise Exception("multiple terms with markup in group")
                    self.prefDoc = term
        self.defs        = self.mergeDefs()
        self.comments    = self.mergeComments()
        self.ncitId      = self.mergeNcitIds()
        self.mediaLinks  = self.mergeMediaLinks()
        self.termTypes   = self.mergeTermTypes()
        self.termSources = self.mergeTermSources()
    def mergeDefs(self):
        defs = {}
        if self.prefDoc:
            terms = [self.prefDoc]
        elif len(self.terms) == 1:
            terms = self.terms
        else:
            terms = [t for t in self.terms if not t.blocked]
        for key in DEF_KEYS:
            defs[key] = MergedDefinition(terms, key[0], key[1], self.lastMod,
                                         self.lastReviewed)
        return defs
    def mergeComments(self):
        return u"" # Sheri says comments go in the term name docs.
    def mergeNcitIds(self):
        ncitId = None
        for t in self.terms:
            if t.thesId:
                if ncitId and ncitId != t.thesId:
                    raise Exception("conflicting thesaurus IDs '%s' and '%s'" %
                                    (ncitId, t.thesId))
                ncitId = t.thesId
        return ncitId
    def mergeMediaLinks(self):
        linkSet = set()
        links = []
        for t in self.terms:
            for m in t.media:
                if m not in linkSet:
                    linkSet.add(m)
                    links.append(m)
        return links
    def mergeTermTypes(self):
        typeSet = set()
        for t in self.terms:
            for tt in t.types:
                typeSet.add(tt)
        return list(typeSet)
    def mergeTermSources(self):
        return u"" # goes in term name doc; see comment #32 of issue #3723
    def makeConceptDoc(self):
        docXml = [u"""\
<?xml version='1.0' encoding='utf-8'?>
<GlossaryTermConcept xmlns:cdr='cips.nci.nih.gov/cdr'>
"""]
        for key in self.defs:
            if key[0] == 'E':
                docXml.append(self.defs[key].toXml())
        docXml += self.mediaLinks
        for key in self.defs:
            if key[0] == 'S':
                docXml.append(self.defs[key].toXml())
        for t in self.termTypes:
            docXml.append(u"<TermType>%s</TermType>" % t)
        if self.ncitId:
            docXml.append(u"NCIThesaurusID>%s</NCIThesaurusID>" % self.ncitId)
        docXml.append(u"\n</GlossaryTermConcept>\n")
        doc = u"".join(docXml)
        filt = ['name:Delete cdr:id attributes']
        result = cdr.filterDoc('guest', filt, doc = doc)
        if type(result) in (str, unicode):
            raise Exception(result)
        return result[0]

def parseErrors(errors):
    if not errors:
        return None
    try:
        dom = xml.dom.minidom.parseString(errors)
        errorStrings = []
        for e in dom.getElementsByTagName('Err'):
            error = cdr.getTextContent(e, True).strip()
            if error:
                errorStrings.append(error)
        if not errorStrings:
            return None
        return errorStrings
    except:
        return errors

if __name__ == '__main__':
    preferredGlossaryDefinitions = set()
    #for line in file('pref-gloss-defs.txt'):
    #    try:
    #        preferredGlossaryDefinitions.add(int(line.strip()))
    #    except:
    #        pass
    #sys.stderr.write("loaded %d preferred glossary definition IDs\n" %
    #                 len(preferredGlossaryDefinitions))
    options = Opts()
    if options.mode == 'TEST':
        now = time.strftime("%Y%m%d%M%H%S")
        dirName = "glossary-terms-%s" % now
        os.mkdir(dirName)
        conceptId = 900000
    else:
        dirName = ""
        now = time.strftime("%Y-%m-%dT%M:%H:%S")
        comment = "Glossary conversion run %s" % now
        session = cdr.login(options.user, options.password)
        errors = cdr.getErrors(session, errorsExpected = False,
                               asSequence = True)
        if errors:
            raise Exception(errors)
    cursor = cdrdb.connect('CdrGuest').cursor()
    groups = getGroups(cursor, options.fileName)
    for group in groups[:options.maxGroups]:
        cdr.logwrite("converting group %s" % (group,), LOGFILE)
        sys.stderr.write("converting group %s\n" % (group,))
        if not dirName:
            checkedOut = []
            for docId in group:
                try:
                    cdr.checkOutDoc(session, docId, force = 'Y',
                                    comment = 'Running Glossary conversion')
                    checkedOut = docId
                except Exception, e:
                    cdr.logwrite("checkOutDoc(%d): %s" % (docId, e), LOGFILE)
                    sys.stderr.write("checkOutDoc(%d): %s\n" % (docId, e))
                    for docId in checkedOut:
                        try:
                            cdr.unlock(session, docId)
                        except:
                            pass
                    raise Exception("can't check out CDR%d" % docId)
        try:
            concept = GlossaryTermConcept(group, cursor)
            conceptDoc = concept.makeConceptDoc()
            if dirName:
                concept.docId = conceptId
                conceptId += 1
                fileName = "%s/CDR%d.xml" % (dirName, concept.docId)
                fp = open(fileName, "w")
                fp.write(conceptDoc)
                fp.close()
            else:
                cdrDoc = """\
<CdrDoc Type='GlossaryTermConcept' Id=''>
 <CdrDocCtl>
  <DocType>GlossaryTermConcept</DocType>
  <DocTitle>Glossary Concept</DocTitle>
 </CdrDocCtl>
 <CdrDocXml><![CDATA[""" + conceptDoc + """]]></CdrDocXml>
</CdrDoc>"""
                docId, errors = cdr.addDoc(session,
                                           doc = cdrDoc,
                                           val = 'Y', ver = 'Y',
                                           showWarnings = True,
                                           comment = comment,
                                           reason = comment)
                errors = parseErrors(errors)
                if not docId:
                    raise Exception(errors)
                concept.docId = int(re.sub("[^\\d]+", "", docId))
                cdr.logwrite("created new concept document %s" % docId, LOGFILE)
                sys.stderr.write("created concept doc %s\n" % docId)
                if errors:
                    cdr.logwrite("%s: %s" % (docId, errors), LOGFILE)
                    sys.stderr.write("%s: %s\n" % (docId, errors))
                try:
                    cdr.unlock(session, docId)
                except:
                    pass
            for term in concept.terms:
                nameDoc = term.makeNameDoc(concept)
                if dirName:
                    fileName = "%s/CDR%d.xml" % (dirName, term.docId)
                    fp = open(fileName, "w")
                    fp.write(nameDoc.encode('utf-8'))
                    fp.close()
                else:
                    cdrDoc = u"""\
<CdrDoc Type='GlossaryTermName' Id='CDR%010d'>
 <CdrDocCtl>
  <DocType>GlossaryTermName</DocType>
 </CdrDocCtl>
 <CdrDocXml><![CDATA[%s]]></CdrDocXml>
</CdrDoc>""" % (term.docId, nameDoc)
                    docId, errors = cdr.repDoc(session,
                                               doc = cdrDoc.encode('utf-8'),
                                               val = 'Y', ver = 'Y',
                                               showWarnings = True,
                                               comment = comment,
                                               reason = comment,
                                               verPublishable = 'N')
                    errors = parseErrors(errors)
                    if not docId:
                        raise Exception(errors)
                    cdr.logwrite("updated name doc %s" % docId, LOGFILE)
                    sys.stderr.write("updated name doc %s\n" % docId)
                    if errors:
                        cdr.logwrite("%s: %s" % (docId, errors), LOGFILE)
                        sys.stderr.write("%s: %s\n" % (docId, errors))
                    try:
                        cdr.unlock(session, docId)
                    except:
                        pass
        except Exception, e:
            cdr.logwrite("conversion failure: %s" % e, LOGFILE, True)
            print "conversion failure: %s" % e
