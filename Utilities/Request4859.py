#----------------------------------------------------------------------
#
# $Id$
#
# Report for Larry Wright.
#
# BZIssue::4859
#
#----------------------------------------------------------------------
import cdrdb, lxml.etree as etree, sys

#----------------------------------------------------------------------
# Extract text recursively from etree element.
#----------------------------------------------------------------------
def getText(e, pieces = None):
    if pieces is None:
        pieces = []
        top = True
    else:
        top = False
    if e.text is not None:
        pieces.append(e.text)
    for child in e:
        getText(child, pieces)
    if e.tail is not None:
        pieces.append(e.tail)
    if top:
        return u"".join(pieces)

class Term:
    def __init__(self, docId, tree):
        self.cdrId = docId
        self.name = self.code = None
        self.definitions = []
        for node in tree.findall('PreferredName'):
            self.name = node.text
        for node in tree.findall('Definition/DefinitionText'):
            self.definitions.append(getText(node))
        for node in tree.findall('OtherName/SourceInformation'
                                 '/VocabularySource'):
            source = code = None
            for child in node:
                if child.tag == 'SourceCode':
                    source = child.text
                elif child.tag == 'SourceTermId':
                    code = child.text
            if source == 'NCI Thesaurus':
                self.code = code

def fix(me):
    if me is None:
        return ""
    me = me.strip().encode('utf-8')
    return me.replace('\n', r'\n').replace('\r', '').replace('\t', r'\t')

cursor = cdrdb.connect('CdrGuest').cursor()
cursor.execute("""\
    SELECT DISTINCT t.doc_id
               FROM query_term t
               JOIN query_term d
                 ON d.doc_id = t.doc_id
              WHERE d.path = '/Term/Definition/DefinitionText/@cdr:id'
                AND t.path = '/Term/SemanticType/@cdr:ref'
                AND t.int_val = (SELECT doc_id
                                   FROM query_term
                                  WHERE path = '/Term/PreferredName'
                                    AND value = 'Drug/agent')
                AND t.int_val NOT IN (SELECT doc_id
                                        FROM query_term
                                       WHERE path = '/Term/TermType'
                                                  + '/TermTypeName'
                                         AND value = 'Obsolete term')""")
docIds = [row[0] for row in cursor.fetchall()]
for docId in docIds:
    cursor.execute("SELECT xml FROM document WHERE id = ?", docId)
    try:
        docXml = cursor.fetchall()[0][0]
        tree = etree.XML(docXml.encode('utf-8'))
        term = Term(docId, tree)
        nDefs = len(term.definitions)
        if nDefs != 1:
            sys.stderr.write("CDR%d has %d definitions\n" % (docId, nDefs))
        for definition in term.definitions:
            print "%d\t%s\t%s\t%s" % (term.cdrId, fix(term.name),
                                      fix(definition), fix(term.code))
    except Exception, e:
        sys.stderr.write("CDR%d: %s\n" % (docId, e))
