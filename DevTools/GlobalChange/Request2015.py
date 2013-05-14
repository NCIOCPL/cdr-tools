#----------------------------------------------------------------------
#
# $Id$
#
# Import drug terminology information from NCI Thesaurus.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdr, cdrdb, sys, ModifyDocs, xml.dom.minidom, NciThesaurus
import ExcelReader, sys, xml.sax.handler, xml.sax.saxutils, re, time

#----------------------------------------------------------------------
# Record for a CDR drug Term document and its corresponding thesaurus
# Concept.
#----------------------------------------------------------------------
class Term:
    def __init__(self, cdrId, name, code, concept = None):
        self.cdrId       = cdrId
        self.name        = name
        self.code        = code
        self.concept     = concept
        self.definitions = []
        self.haveDefs    = False
    def __cmp__(self, other):
        return cmp(self.code, other.code)

#----------------------------------------------------------------------
# Escape special characters in an XML string.
#----------------------------------------------------------------------
def fix(xmlString):
    return xmlString and xml.sax.saxutils.escape(xmlString) or u""

#----------------------------------------------------------------------
# Holds information for one VocabularySource element.
#----------------------------------------------------------------------
class VocabularySource:
    def __init__(self, sourceCode = None, sourceTermType = None,
                 sourceTermId = None):
        self.sourceCode     = sourceCode
        self.sourceTermType = sourceTermType
        self.sourceTermId   = sourceTermId
    def toXml(self):
        xmlString = [u"<VocabularySource>"
                     u"<SourceCode>%s</SourceCode>"
                     u"<SourceTermType>%s</SourceTermType>" %
                     (fix(self.sourceCode), fix(self.sourceTermType))]
        if self.sourceTermId:
            xmlString.append(u"<SourceTermId>%s</SourceTermId>" %
                             fix(self.sourceTermId))
        xmlString.append(u"</VocabularySource>")
        return u"".join(xmlString)
        
#----------------------------------------------------------------------
# Holds information for a SourceInformation element.
#----------------------------------------------------------------------
class SourceInformation:
    def __init__(self, vocabularySources = None, referenceSource = None):
        self.vocabularySources = vocabularySources or []
        self.referenceSource   = referenceSource
    def toXml(self):
        if not (self.vocabularySources or self.referenceSource):
            return u""
        xmlString = [u"<SourceInformation>"]
        if self.referenceSource:
            xmlString.append(u"<ReferenceSource>%s</ReferenceSource>"
                             % fix(self.referenceSource))
        for source in self.vocabularySources:
            xmlString.append(source.toXml())
        xmlString.append(u"</SourceInformation>")
        return u"".join(xmlString)
        
#----------------------------------------------------------------------
# Holds one OtherName element's information.
#----------------------------------------------------------------------
class OtherTermName:
    def __init__(self, name, types = None, sourceInfo = None,
                 reviewStatus = None, comment = None):
        self.name         = name
        self.types        = types or []
        self.sourceInfo   = sourceInfo or SourceInformation()
        self.reviewStatus = reviewStatus
        self.comment      = comment
        self.used         = False
    def toXml(self):
        xmlString = [u"<OtherName>"
                     u"<OtherTermName>%s</OtherTermName>" % fix(self.name)]
        for nameType in self.types:
            xmlString.append(u"<OtherNameType>%s</OtherNameType>" %
                             fix(nameType))
        if self.sourceInfo:
            xmlString.append(self.sourceInfo.toXml())
        if self.reviewStatus:
            xmlString.append(u"<ReviewStatus>%s</ReviewStatus>" %
                             fix(self.reviewStatus))
        if self.comment:
            xmlString.append(u"<Comment>%s</Comment>" % fix(self.comment))
        xmlString.append(u"</OtherName>")
        return u"".join(xmlString)
        
#----------------------------------------------------------------------
# Extracts OtherTermName objects from CDR Term documents.
#----------------------------------------------------------------------
class OtherNameParser(xml.sax.handler.ContentHandler):
    def startDocument(self):
        self.otherNames    = []
        self.path          = []
        self.inOtherName   = False
        self.inVocabSource = False
        self.textContent   = u''
    def startElement(self, name, attributes):
        self.path.append(name)
        self.textContent= u''
        if name == "OtherName":
            self.inOtherName  = True
            self.name         = None
            self.nameTypes    = []
            self.sourceInfo   = SourceInformation()
            self.reviewStatus = None
            self.comment      = None
        elif name == "VocabularySource":
            self.vocabularySource = VocabularySource()
    def endElement(self, name):
        self.path.pop()
        if self.inOtherName:
            if name == "OtherName":
                self.inOtherName = False
                self.otherNames.append(OtherTermName(self.name, self.nameTypes,
                                                     self.sourceInfo,
                                                     self.reviewStatus,
                                                     self.comment))
            elif name == "OtherTermName":
                self.name = self.textContent
            elif name == "OtherNameType":
                self.nameTypes.append(self.textContent)
            elif name == "ReferenceSource":
                self.sourceInfo.referenceSource = self.textContent
            elif name == "VocabularySource":
                self.sourceInfo.vocabularySources.append(self.vocabularySource)
            elif self.path[-1] == "VocabularySource":
                if name == "SourceCode":
                    self.vocabularySource.sourceCode = self.textContent
                elif name == "SourceTermType":
                    self.vocabularySource.sourceTermType = self.textContent
                elif name == "SourceTermId":
                    self.vocabularySource.sourceTermId = self.textContent
            elif name == "ReviewStatus":
                self.reviewStatus = self.textContent
            elif name == "Comment":
                self.comment = self.textContent
    def characters(self, content):
        self.textContent += content

class Mismatch:
    def __init__(self, thesaurusName, cdrName, conceptCode):
        self.thesaurusName = thesaurusName
        self.cdrName       = cdrName
        self.conceptCode   = conceptCode

#----------------------------------------------------------------------
# Set of all CDR drug Term documents for which we want to import
# NCI Thesaurus Concept information.
#----------------------------------------------------------------------
class CdrDrugTerms:
    def __init__(self, bookName = 'NciThesaurus-20060726.xls',
                 thesaurusFile = 'Thesaurus-060725.xml'):
        """
        Pass in filename for Excel workbook containing one row for each
        drug term for which we want to import thesaurus information,
        with the first column containing the CDR ID for the drug term,
        and the fourth column containing the NCIt concept code.  Also
        pass in the filename for the XML document containing concepts
        from the NCI Thesaurus.
        """
        self.terms            = {}
        self.notInThesaurus   = {}
        self.notInCdr         = {}
        self.needReview       = {}
        self.haveDefinitions  = {}
        self.noDefInThesaurus = {}
        self.mismatchedNames  = {}

        # Build a set of Term documents in the CDR.
        conn = cdrdb.connect('CdrGuest')
        cursor = conn.cursor()
        cursor.execute("""\
            SELECT doc_id, value
              FROM query_term
             WHERE path = '/Term/PreferredName'""")
        termNames = {}
        for cdrId, termName in cursor.fetchall():
            termNames[cdrId] = termName

        # Build a list of documents which already have definitions.
        cursor.execute("""\
   SELECT DISTINCT doc_id
              FROM query_term
             WHERE path = '/Term/Definition/DefinitionType'""")
        termsWithDefinitions = set([row[0] for row in cursor.fetchall()])

        # Collect the CDR IDs and NCIt concept codes for the terms we want.
        excelMap = {}
        conceptCodes = set()
        book = ExcelReader.Workbook(bookName)
        sheet = book[0]
        self.numSpreadsheetRows = 0
        for row in sheet:
            self.numSpreadsheetRows += 1
            if row.number > 0:
                cdrId = int(row[0].val)
                code = str(row[3].val).strip().upper()
                if cdrId not in termNames:
                    self.notInCdr[cdrId] = code
                elif cdrId in termsWithDefinitions:
                    self.haveDefinitions[cdrId] = code
                else:
                    excelMap[cdrId] = code
                    conceptCodes.add(code)

        # Walk through the NCI Thesaurus, looking for our target conceptCodes.
        parser = NciThesaurus.Thesaurus(conceptCodes)
        xml.sax.parse(thesaurusFile, parser)
        self.conceptsInThesaurus = parser.numConcepts
        for cdrId in excelMap:
            code = excelMap[cdrId]
            if code in parser.terms:
                concept = parser.terms[code]
                term = Term(cdrId, termNames[cdrId], code, concept)
                if concept.needsReview:
                    self.needReview[cdrId] = term
                elif not concept.definitions:
                    self.noDefInThesaurus[cdrId] = term
                else:
                    mismatch = None
                    if not concept.preferredName:
                        mismatch = Mismatch(None, termNames[cdrId], code)
                    else:
                        ucThesaurusName = concept.preferredName.upper()
                        if termNames[cdrId].upper() != ucThesaurusName:
                            mismatch = Mismatch(concept.preferredName,
                                                termNames[cdrId], code)
                    if mismatch:
                        self.mismatchedNames[cdrId] = mismatch
                    else:
                        self.terms[cdrId] = term
            else:
                self.notInThesaurus[cdrId] = code

    def report(self):
        when = time.strftime("%Y-%m-%d")
        html = [u"""\
<html>
 <head>
  <meta http-equiv='Content-Type' content='text/html; charset=utf-8'>
  <style type='text/css'>
   body { font-family: Arial }
   .red { color: red }
  </style>
  <title>Imported Concepts %s</title>
 </head>
 <body>
  <h1>Imported Concepts %s</h1>
  <table border='1' cellpadding='3' cellspacing='0'>
   <tr>
    <th>NCI ID</th>
    <th>CDR ID</th>
    <th>CDR PT</th>
    <th>Definition(s)</th>
   </tr>
""" % (when, when)]
        cdrIds = self.terms.keys()
        cdrIds.sort()
        for cdrId in cdrIds:
            term = self.terms[cdrId]
            defs = term.definitions
            if len(defs) > 1:
                color = u'red'
                rowspan = u" rowspan='%d'" % len(defs)
            else:
                rowspan = u""
                color = u'black'
                if not defs:
                    defs = [u""]
            html.append(u"""\
   <tr>
    <td valign='top'%s>%s</td>
    <td valign='top'%s>%d</td>
    <td valign='top'%s>%s</td>
    <td valign='top' class='%s'>%s</td>
   </tr>
""" % (rowspan, term.code,
       rowspan, cdrId,
       rowspan, fix(term.name),
       color, defs[0] and fix(defs[0]) or u"&nbsp;"))
            for d in defs[1:]:
                html.append(u"""\
   <tr>
    <td valign='top'>%s</td>
   </tr>
""" % (d and fix(d) or u"&nbsp;"))
        html.append(u"""\
  </table>
 </body>
</html>
""")
        f = open(time.strftime('DrugTermImport-%Y%m%d.html'), 'w')
        f.write(u"".join(html).encode('utf-8'))
        f.close()
                 
    def logProblems(self, job):
        for cdrId in self.notInCdr:
            job.log("CDR%s (concept %s) not found in CDR" %
                    (cdrId, self.notInCdr[cdrId]))
        for cdrId in self.haveDefinitions:
            job.log("CDR%s (concept %s) already has a CDR definition" %
                    (cdrId, self.haveDefinitions[cdrId]))
        for cdrId in self.notInThesaurus:
            job.log("Concept ID %s for CDR%s not found in NCI Thesaurus" %
                    (self.notInThesaurus[cdrId], cdrId))
        for cdrId in self.noDefInThesaurus:
            job.log("Concept ID %s for CDR%s has no definition "
                    "in the NCI Thesaurus" %
                    (self.noDefInThesaurus[cdrId].code, cdrId))
        for cdrId in self.needReview:
            job.log("Concept %s (CDR%s) marked 'Definition needs review'" %
                    (self.needReview[cdrId].code, cdrId))
        for cdrId in self.mismatchedNames:
            mismatch = self.mismatchedNames[cdrId]
            job.log("CDR%s (concept %s) has preferred name '%s' "
                    "but NCIT has preferred name '%s'" %
                    (cdrId, mismatch.conceptCode, mismatch.cdrName,
                     mismatch.thesaurusName))
        job.log("%d rows in mapping spreadsheet" % self.numSpreadsheetRows)
        job.log("%d concepts not found in CDR" % len(self.notInCdr))
        job.log("%d concepts already have a CDR definition" %
                len(self.haveDefinitions))
        job.log("%d concepts not found in NCI Thesaurus" %
                len(self.notInThesaurus))
        job.log("%d concepts have no definition in the NCI Thesaurus" %
                len(self.noDefInThesaurus))
        job.log("%d concepts marked 'Definition needs review'" %
                len(self.needReview))
        job.log("%d concepts have preferred names which do not match "
                "the corresponding CDR term's preferred name" %
                len(self.mismatchedNames))

#----------------------------------------------------------------------
# The Filter class is given to the ModifyDocs.Job object, which invokes
# the getDocIds() method to retrieve a list of CDR document IDs for
# processing.
#----------------------------------------------------------------------
class Filter:
    def __init__(self, terms):
        self.terms = terms
    def getDocIds(self):
        return self.terms.keys()

#----------------------------------------------------------------------
# The Transform class is given to the ModifyDocs.Job object, which in
# turn gives it to each ModifyDocs.Doc object.  The run() method of
# this class takes a cdr.Doc object and returns a (possibly) modified
# copy of that object's xml member.
#
# See comment at top for this job's logic.
#----------------------------------------------------------------------
class Transform:
    thesaurusYearPattern = re.compile(u"\\s*\(?NCI\\d\\d\)?\\s*$")
    def __init__(self, terms, parser):
        self.terms  = terms
        self.parser = parser

    def run(self, docObj):

        # Make sure we have a way to know where to put the imported data.
        if docObj.xml.find('<PreferredName') == -1:
            self.job.log("%s: missing PreferredName element")
            return docObj.xml

        # Strip out OtherName and Definition elements, leaving placeholders.
        filter = """\
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

 <!-- Drop these. -->
 <xsl:template                  match = 'OtherName | Definition' />

 <!-- Add placeholders after the required PreferredName element. -->
 <xsl:template                  match = 'PreferredName'>
  <xsl:copy>
   <xsl:apply-templates        select = '@*|node()|comment()|
                                         processing-instruction()'/>
  </xsl:copy>
  <xsl:text>@@OTHERNAMES@@@@DEFINITION@@</xsl:text>
 </xsl:template>
</xsl:transform>
"""
        result = cdr.filterDoc('guest', filter, doc = docObj.xml, inline = 1)
        if type(result) in (str, unicode):
            message = "%s: %s" % (docObj.id, result)
            if type(message) is unicode:
                message = message.encode('utf-8')
            self.job.log(message)
            return docObj.xml
        return self.replacePlaceholders(docObj, result[0])

    def replacePlaceholders(self, docObj, xmlWithPlaceholders):
        docIds  = cdr.exNormalize(docObj.id)
        term    = self.terms[docIds[1]]
        concept = term.concept
        xml.sax.parseString(docObj.xml, self.parser)
        self.newOtherNames = []
        if concept.preferredName:
            self.importOtherName(concept.preferredName, # u'Synonym',
                                 u'Lexical variant', u'PT',
                                 concept.code)
        for fullSyn in concept.fullSyn:
            if fullSyn.termGroup != 'PT':
                self.importOtherName(fullSyn.termName,
                                     self.lookupType(fullSyn.termGroup),
                                     fullSyn.termGroup)
        for indCode in concept.indCodes:
            self.importOtherName(indCode, u'IND code', u'IND_Code')
        for nscCode in concept.nscCodes:
            self.importOtherName(nscCode, u'NSC number', u'NSC_Code')
        for casCode in concept.casCodes:
            self.importOtherName(casCode, u'CAS Registry name',
                                 u'CAS_Registry')
        otherNames = self.parser.otherNames + self.newOtherNames
        for otherName in self.parser.otherNames:
            if not otherName.used:
                name = otherName.name.encode('utf-8')
                nameLog.write("CDR%010d: %s\n" % (term.cdrId, name))
                nameLog.flush()
        # self.job.log('milestone 1')
        if otherNames:
            otherNames = (u"\n" +
                          u"\n".join([o.toXml() for o in otherNames]) + u"\n")
        else:
            otherNames = u""
        definitions = []
        # self.job.log('milestone 2')
        for definition in concept.definitions:
            strippedDefinition = Transform.thesaurusYearPattern.sub(u'',
                                                          definition.text)
            if not term.haveDefs:
                term.definitions.append(strippedDefinition)
            definitions.append(u"""\
<Definition>
<DefinitionText>%s</DefinitionText>
<DefinitionType>Health professional</DefinitionType>
<DefinitionSource>
<DefinitionSourceName>NCI Thesaurus</DefinitionSourceName>
</DefinitionSource>
<ReviewStatus>Reviewed</ReviewStatus>
</Definition>
""" % fix(strippedDefinition))
        term.haveDefs = True
        definitions = u"".join(definitions)
        # self.job.log('milestone 3')
        docXml =  (xmlWithPlaceholders.replace("@@OTHERNAMES@@",
                                               otherNames.encode('utf-8'), 1)
                                      .replace("@@DEFINITION@@",
                                               definitions.encode('utf-8'), 1))
        # Just in case we have multiple preferred names.
        # self.job.log('milestone 4')
        return docXml.replace("@@OTHERNAMES@@@@DEFINITION@@", "")

    #----------------------------------------------------------------------
    # Logic from Lakshmi: if exactly one OtherTermName matches without
    # regard for case, use it.  Otherwise, if more than one such match
    # if found, and only one matches with regard to case, use it.
    # Otherwise, complain and add a new OtherTerm element.
    #----------------------------------------------------------------------
    def findOtherName(self, name):
        strippedName = name.strip()
        lowerName    = strippedName.lower()
        matches      = []
        exactMatches = []
        for otherName in self.parser.otherNames:
            thisStrippedName = otherName.name.strip()
            if thisStrippedName.lower() == lowerName:
                matches.append(otherName)
                if strippedName == thisStrippedName:
                    exactMatches.append(otherName)
        if not matches:
            return None
        if len(matches) == 1:
            return matches[0]
        if len(exactMatches) == 1:
            return exactMatches[0]
        message = (u"multiple matches for OtherTermName '%s': %s" %
                   (strippedName,
                    u"; ".join([(u'"%s"' % n.name) for n in matches])))
        self.job.log(message.encode('utf-8'))
        return None

    def importOtherName(self, name, cdrType, sourceType, sourceId = None):
        oldOtherName = self.findOtherName(name)
        if oldOtherName:
            oldOtherName.used = True
            if oldOtherName.comment:
                comment = oldOtherName.comment.strip()
                if comment:
                    if comment[-1] in u".!?":
                        comment += u"  N"
                    else:
                        comment += u"; n"
                else:
                    comment = u"N"
            else:
                comment = u"N"
            comment += (u"ame matches (case insensitive) synonym in file "
                        u"extracted from the NCI Thesaurus %s as of %s." %
                        (thesDate, jobDate))
            oldOtherName.comment = comment
            if sourceId:
                vocabSource = VocabularySource(u'NCI Thesaurus',
                                               sourceType, sourceId)
                oldOtherName.sourceInfo.vocabularySources.append(vocabSource)
                if oldOtherName.reviewStatus != 'Problematic':
                    oldOtherName.reviewStatus = 'Reviewed'
            elif (len(oldOtherName.types) != 1 or
                  cdrType != oldOtherName.types[0]):
                #oldOtherName.types.append(cdrType)
                oldOtherName.types = [cdrType]
        else:
            vocabSource = VocabularySource(u'NCI Thesaurus',
                                           sourceType, sourceId)
            sourceInfo = SourceInformation([vocabSource])
            newName = OtherTermName(name, [cdrType], sourceInfo, 'Reviewed')
            self.newOtherNames.append(newName)

    def lookupType(self, nciThesaurusType):
        otherNameType = {
            "PT"               : "Preferred term",
            "AB"               : "Abbreviation",
            "AQ"               : "Obsolete name",
            "BR"               : "US brand name",
            "CN"               : "Code name",
            "FB"               : "Foreign brand name",
            "SN"               : "Chemical structure name",
            "SY"               : "Synonym",
            "INDCode"          : "IND_Code",
            "NscCode"          : "NSC_Code",
            "CAS_Registry_Name": "CAS_Registry" 
        }.get(nciThesaurusType)
        if not otherNameType:
            self.job.log("unrecognized NCI thesaurus name type: %s" %
                         nciThesaurusType.encode('utf-8'))
            return nciThesaurusType
        return otherNameType

#----------------------------------------------------------------------
# Processing starts here.
#----------------------------------------------------------------------
if len(sys.argv) < 6:
    sys.stderr.write("usage: %s uid pwd workbook thesaurus thes-date [LIVE]\n"
                     % sys.argv[0])
    sys.exit(1)

testMode  = len(sys.argv) < 7 or sys.argv[6] != "LIVE"
thesDate  = sys.argv[5]
jobDate   = time.strftime("%Y-%m-%d")
drugTerms = CdrDrugTerms(sys.argv[3], sys.argv[4])
parser    = OtherNameParser()
transform = Transform(drugTerms.terms, parser)
nameLog   = file('UnmatchedOtherNames.log', 'w')
job       = ModifyDocs.Job(sys.argv[1], sys.argv[2], Filter(drugTerms.terms),
                           transform,
                           "Importing thesaurus information (request #2015).",
                           testMode = testMode)
transform.job = job
drugTerms.logProblems(job)
job.log("%d concepts found in NCI Thesaurus file" %
        drugTerms.conceptsInThesaurus)
job.run()
drugTerms.report()
nameLog.close()
