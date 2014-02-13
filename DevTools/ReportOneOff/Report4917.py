#----------------------------------------------------------------------
#
# $Id$
#
# Report for Mauricio.
#
# BZIssue::4917
#
#----------------------------------------------------------------------
import ExcelWriter, sys, cdrdb, lxml.etree as etree, cgi

class Concept:
    def __init__(self, docId):
        cursor.execute("SELECT xml FROM document WHERE id = ?", docId)
        docXml = cursor.fetchall()[0][0]
        fp = open('Report4917/concept-%d.xml' % docId, 'wb')
        fp.write(docXml.encode('utf-8'))
        fp.close()
        tree = etree.XML(docXml.encode('utf-8'))
        engDefs = tree.findall('TermDefinition/DefinitionText')
        spanDefs = tree.findall('TranslatedTermDefinition/DefinitionText')
        self.numEnglishDefinitions = len(engDefs)
        self.numSpanishDefinitions = len(spanDefs)
        self.engPlaceHolders = []
        self.spanPlaceHolders = []
        for engDef in engDefs:
            for ph in engDef.findall('PlaceHolder'):
                name = ph.get('name')
                if name:
                    self.engPlaceHolders.append(name)
        for spanDef in spanDefs:
            for ph in spanDef.findall('PlaceHolder'):
                name = ph.get('name')
                if name:
                    self.spanPlaceHolders.append(name)
    def hasOneDefinitionPerLanguage(self):
        if self.numEnglishDefinitions != 1:
            return False
        if self.numSpanishDefinitions != 1:
            return False
        return True
    def hasPlaceHoldersForBothLanguages(self):
        return self.engPlaceHolders and self.spanPlaceHolders
    def wanted(self):
        if not self.hasOneDefinitionPerLanguage():
            return False
        return self.hasPlaceHoldersForBothLanguages()

def getDefinitionString(d):
    s = etree.tostring(d).replace('<DefinitionText>',
                                  '').replace('</DefinitionText>', '')
    tree = etree.XML("<s>%s</s>" % s.replace('<',
                                             '@@LT@@').replace('>',
                                                               '@@GT@@'))
    return tree.text.replace('@@LT@@', '<').replace('@@GT@@', '>').encode('utf-8')
    
class Name:
    def __init__(self, docId):
        cursor.execute("SELECT xml FROM pub_proc_cg WHERE id = ?", docId)
        rows = cursor.fetchall()
        if not rows:
            raise Exception("CDR%d not published" % docId)
        docXml = rows[0][0]
        self.docId = docId
        self.engNames = []
        self.spanNames = []
        self.engDefs = []
        self.spanDefs = []
        tree = etree.XML(docXml.encode('utf-8'))
        for node in tree.findall('TermName'):
            self.engNames.append(node.text)
        for node in tree.findall('SpanishTermName'):
            self.spanNames.append(node.text)
        self.engDefs = [getDefinitionString(d) for d in
                        tree.findall('TermDefinition/DefinitionText')]
        self.spanDefs = [getDefinitionString(d) for d in
                         tree.findall('SpanishTermDefinition/DefinitionText')]
    def wanted(self):
        if len(self.engNames) != 1 or len(self.spanNames) != 1:
            return False
        if len(self.engDefs) != 1 or len(self.spanDefs) != 1:
            return False
        return True

book = ExcelWriter.Workbook()
rowNumber = 1
sheet1 = book.addWorksheet('English')
sheet2 = book.addWorksheet('Spanish')
cursor = cdrdb.connect('CdrGuest').cursor()
cursor.execute("""\
    SELECT int_val, COUNT(*)
      FROM query_term
     WHERE path = '/GlossaryTermName/GlossaryTermConcept/@cdr:ref'
  GROUP BY int_val
    HAVING count(*) > 4""")
conceptIds = [row[0] for row in cursor.fetchall()]
for conceptId in conceptIds:
    try:
        concept = Concept(conceptId)
        if not concept.wanted():
            sys.stderr.write("concept %d: %d English defs, %d Spanish defs\n" %
                             (conceptId, concept.numEnglishDefinitions,
                              concept.numSpanishDefinitions))
            continue
    except Exception, e:
        sys.stderr.write("concept %d: %s\n" % (conceptId, e))
        continue
    cursor.execute("""\
        SELECT doc_id
          FROM query_term
         WHERE path = '/GlossaryTermName/GlossaryTermConcept/@cdr:ref'
           AND int_val = ?""", conceptId)
    nameIds = [row[0] for row in cursor.fetchall()]
    for nameId in nameIds:
        try:
            name = Name(nameId)
        except Exception, e:
            sys.stderr.write("term %d: %s\n" % (nameId, e))
            continue
        if not name.wanted():
            sys.stderr.write("term %d: %d English names %d defs); "
                             "%d Spanish names (%d defs)\n" %
                             (len(name.engNames), len(name.spanNames),
                              len(name.engDefs), len(name.spanDefs)))
            continue
        fp = open('Report4917/name-%d.txt' % nameId, 'wb')
        fp.write("English Name: %s\n" % name.engNames[0].encode('utf-8'))
        fp.write("Spanish Name: %s\n" % name.spanNames[0].encode('utf-8'))
        fp.write("English Definition: %s\n" % name.engDefs[0])
        fp.write("Spanlish Definition: %s\n" % name.spanDefs[0])
        fp.close()
        row = sheet1.addRow(rowNumber)
        row.addCell(1, nameId)
        row.addCell(2, name.engNames[0])
        row.addCell(3, unicode(name.engDefs[0], 'utf-8'))
        row = sheet2.addRow(rowNumber)
        row.addCell(1, nameId)
        row.addCell(2, name.spanNames[0])
        row.addCell(3, unicode(name.spanDefs[0], 'utf-8'))
        rowNumber += 1
        break
        #fp = open('Report4917/CDR%d-cdr.xml' % nameId, 'wb')
        #fp.write(nameDoc.cdrXml.encode('utf-8'))
        #fp.close()
fp = open('Report4917.xls', 'wb')
book.write(fp, True)
fp.close()
