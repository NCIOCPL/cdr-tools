#----------------------------------------------------------------------
#
# $Id$
#
# Import drug terminology information from PDQ Thesaurus.
#
# "We need to import information from the NCI Thesaurus into the CDR
# Terminology documents. The steps for this are as follows:
#
# 1. A spreadsheet with a list of 500 drugs whose definitions have been
#    vetted and entered in the NCI THesaurus by CIAT will be attached to
#    this issue. 
#
# 2. This spreadsheet will be used to identify the Concept Codes for which
#    we need to download data from the NCI Thesaurus. In addition, the
#    spreadsheet has the CDR Preferred Term which we will use to identify
#    the CDRID of the matching CDR drug document.
#
# 3. For the Concept Codes identified in this list, we have to obtain data
#    from NCICB. For the given Concept Code, we need to get the Preferred
#    Name, the FULL_SYN subelements that have NCI or NCI-GLOSS as a term-
#    source. We also need the Definition subelemetns with NCI as definition
#    source. We also need the IND_Code and NSC_Code."
#
# BZIssue::1592
#
#----------------------------------------------------------------------
import cdr, cdrdb, sys, ModifyDocs, xml.dom.minidom, PdqThesaurus
import ExcelReader, sys, xml.sax.handler, xml.sax.saxutils, re

#----------------------------------------------------------------------
# Record for a CDR drug Term document and its corresponding thesaurus
# Concept.
#----------------------------------------------------------------------
class Term:
    def __init__(self, cdrId, code, concept = None):
        self.cdrId   = cdrId
        self.code    = code
        self.concept = concept

#----------------------------------------------------------------------
# Escape special characters in an XML string.
#----------------------------------------------------------------------
def fix(xmlString):
    return xml.sax.saxutils.escape(xmlString)

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
        xmlString = (u"<VocabularySource>"
                     u"<SourceCode>%s</SourceCode>"
                     u"<SourceTermType>%s</SourceTermType>" %
                     (fix(self.sourceCode), fix(self.sourceTermType)))
        if self.sourceTermId:
            xmlString += (u"<SourceTermId>%s</SourceTermId>" %
                          fix(self.sourceTermId))
        return xmlString + u"</VocabularySource>"
        
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
        xmlString = u"<SourceInformation>"
        if self.referenceSource:
            xmlString += (u"<ReferenceSource>%s</ReferenceSource>"
                          % fix(self.referenceSource))
        if self.vocabularySources:
            for source in self.vocabularySources:
                xmlString += source.toXml()
        return xmlString + u"</SourceInformation>"
        
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
        xmlString = (u"<OtherName>"
                     u"<OtherTermName>%s</OtherTermName>" % fix(self.name))
        for nameType in self.types:
            xmlString += (u"<OtherNameType>%s</OtherNameType>" % fix(nameType))
        if self.sourceInfo:
            xmlString += self.sourceInfo.toXml()
        if self.reviewStatus:
            xmlString += (u"<ReviewStatus>%s</ReviewStatus>" %
                          fix(self.reviewStatus))
        if self.comment:
            xmlString += (u"<Comment>%s</Comment>" % fix(self.comment))
        return xmlString + u"</OtherName>"
        
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
        
#----------------------------------------------------------------------
# Set of all CDR drug Term documents for which we want to import
# PDQ Thesaurus Concept information.
#----------------------------------------------------------------------
class CdrDrugTerms:
    def __init__(self, bookName = 'drug-terms.xls',
                 thesaurusFile = 'terminology.xml'):
        """
        Pass in filename for Excel workbook containing one row for each
        drug term for which we want to import thesaurus information,
        with the first column containing the PDQ name for the drug term,
        which should match the PreferredName element in the CDR Term
        document.  Also pass in the filename for the XML document
        containing concepts from the PDQ Thesaurus.
        """
        self.terms           = {}
        self.excelDuplicates = {}
        self.cdrDuplicates   = {}
        self.unmapped        = {}
        self.notInThesaurus  = {}

        # Get the map from PDQ preferred names to Thesaurus concept codes.
        excelMap = {}
        book = ExcelReader.Workbook(bookName)
        sheet = book[0]
        for row in sheet:
            if row.number > 0:
                name = str(row[1]).strip().lower()
                code = str(row[0]).strip().upper()
                if name in self.excelDuplicates:
                    self.excelDuplicates[name].append(code)
                elif name in excelMap:
                    oldCode = excelMap[name]
                    self.excelDuplicates[name] = [oldCode, code]
                    del excelMap[name]
                else:
                    excelMap[name] = code

        # Build the map from CDR term names to CDR document IDs.
        terms = {}
        conn = cdrdb.connect('CdrGuest')
        cursor = conn.cursor()
        cursor.execute("""\
            SELECT doc_id, value
              FROM query_term
             WHERE path = '/Term/PreferredName'""")
        for cdrId, termName in cursor.fetchall():
            key = termName.strip().lower()
            if key in self.cdrDuplicates:
                self.cdrDuplicates[key].append(cdrId)
            elif key in terms:
                oldId = terms[key]
                self.cdrDuplicates[key] = [oldId, cdrId]
            else:
                terms[key] = cdrId

        # Join the two maps together.
        conceptCodes = {}
        for name in excelMap:
            code = excelMap[name]
            if name in terms:
                cdrId = terms[name]
                self.terms[cdrId] = Term(cdrId, code)
                conceptCodes[code] = True
            else:
                self.unmapped[name] = code

        # Walk through the PDQ Thesaurus, looking for our target conceptCodes.
        parser = PdqThesaurus.Thesaurus(conceptCodes)
        xml.sax.parse(thesaurusFile, parser)
        for cdrId in self.terms:
            term = self.terms[cdrId]
            if term.code in parser.terms:
                term.concept = parser.terms[term.code]
            else:
                self.notInThesaurus[cdrId] = term
        for cdrId in self.notInThesaurus:
            del self.terms[cdrId]

    def logProblems(self, job):
        for name in self.excelDuplicates:
            job.log("ambiguous PDQ preferred name '%s': Concept IDs %s" %
                    (name.encode('utf-8'),
                     ", ".join(self.excelDuplicates[name])))
        for name in self.unmapped:
            code = self.unmapped[name]
            if name in self.cdrDuplicates:
                idStrings = [str(i) for i in self.cdrDuplicates[name]]
                job.log("ambiguous PreferredName '%s' (Concept ID %s): "
                        "CDR Term IDs %s" %
                        (name.encode('utf-8'), code, ", ".join(idStrings)))
            else:
                job.log("PDQ preferred name '%s' (Concept ID %s) "
                        "not found in the CDR" % (name.encode('utf-8'), code))
        for cdrId in self.notInThesaurus:
            job.log("Concept ID %s for CDR%s not found in PDQ Thesaurus" %
                    (self.notInThesaurus[cdrId].code, cdrId))

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
            job.log("%s: missing PreferredName element")
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
        if type(result) in (type(""), type(u"")):
            message = "%s: %s" % (docObj.id, result)
            if type(message) is unicode:
                message = message.encode('utf-8')
            self.job.log(message)
            return docObj.xml
        return self.replacePlaceholders(docObj, result[0])

    def replacePlaceholders(self, docObj, xmlWithPlaceholders):
        docIds  = cdr.exNormalize(docObj.id)
        concept = self.terms[docIds[1]].concept
        xml.sax.parseString(docObj.xml, self.parser)
        self.newOtherNames = []
        if concept.preferredName:
            self.importOtherName(concept.preferredName, u'Synonym', u'PT',
                                 concept.code)
        for fullSyn in concept.fullSyn:
            if fullSyn.termGroup != 'PT':
                self.importOtherName(fullSyn.termName,
                                     self.lookupType(fullSyn.termGroup),
                                     fullSyn.termGroup)
        for indCode in concept.indCodes:
            self.importOtherName(indCode, u'IND code', u'IND_Code')
        for nscCode in concept.nscCodes:
            self.importOtherName(nscCode, u'NSC code', u'NSC_Code')
        for casCode in concept.casCodes:
            self.importOtherName(casCode, u'CAS Registry name',
                                 u'CAS_Registry')
        otherNames = self.parser.otherNames + self.newOtherNames
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
        self.log(message.encode('utf-8'))
        return None

    def importOtherName(self, name, cdrType, sourceType, sourceId = None):
        oldOtherName = self.findOtherName(name)
        if oldOtherName:
            oldOtherName.used = True
            if sourceId:
                vocabSource = VocabularySource(u'NCI Thesaurus',
                                               sourceType, sourceId)
                oldOtherName.sourceInfo.vocabularySources.append(vocabSource)
                if oldOtherName.reviewStatus != 'Problematic':
                    oldOtherName.reviewStatus = 'Reviewed'
            elif cdrType not in oldOtherName.types:
                oldOtherName.types.append(cdrType)
        else:
            vocabSource = VocabularySource(u'NCI Thesaurus',
                                           sourceType, sourceId)
            sourceInfo = SourceInformation([vocabSource])
            newName = OtherTermName(name, [cdrType], sourceInfo, 'Reviewed')
            self.newOtherNames.append(newName)

    def lookupType(self, pdqThesaurusType):
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
        }.get(pdqThesaurusType)
        if not otherNameType:
            self.job.log("unrecognized PDQ thesaurus name type: %s" %
                         pdqThesaurusType.encode('utf-8'))
            return pdqThesaurusType
        return otherNameType

#----------------------------------------------------------------------
# Processing starts here.
#----------------------------------------------------------------------
if len(sys.argv) < 5:
    sys.stderr.write("usage: %s uid pwd workbook thesaurus [LIVE]\n"
                     % sys.argv[0])
    sys.exit(1)

testMode  = len(sys.argv) < 6 or sys.argv[5] != "LIVE"
drugTerms = CdrDrugTerms(sys.argv[3], sys.argv[4])
parser    = OtherNameParser()
transform = Transform(drugTerms.terms, parser)
job       = ModifyDocs.Job(sys.argv[1], sys.argv[2], Filter(drugTerms.terms),
                           transform,
                           "Importing thesaurus information (request #1592).",
                           testMode = testMode)
transform.job = job
drugTerms.logProblems(job)
job.run()
