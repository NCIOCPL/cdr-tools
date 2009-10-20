#!/usr/bin/python

import re, sys, xml.sax.handler, xml.sax.saxutils, ExcelReader

"""

$Id$

Module for extracting Concept records from the NCI Thesaurus.

Structure of the XML Thesaurus document is something like the following:

terminology
    namespaceDef
    kindDef
    roleDef
    propertyDef
    conceptDef
        name
        code
        id
        namespace
        primitive
        kind
        definingConcepts
            concept
        definingRoles
            role
                all | some
                name
                value
            roleGroup
                role
        properties
            property
                name (FULL_SYN, DEFINITION, CAS_Registry, etc.)
                locale
                value
                    <![CDATA[
                        term-name
                        term-group (PT, etc.)
                        term-source (NCI, NCI-GLOSS, etc.)
                        source-code
                    ]]> (for FULL_SYN)
                    <![CDATA[
                        def-source
                        def-definition
                    ]]> (for DEFINITION)


When this module was originally written, we found:
    
39583 concepts

term sources:
    CADSR
    JAX
    CTRM
    FDA_CDER
    KEGG
    NCI-GLOSS
    NCI
    RAEB-2
    RAEB-1
    NCICB
    DTP
    BIOCARTA

term groups:
    DN
    SY
    AB
    CN
    PT (preferred term)
    CI
    AQ
    FB
    CU
    SN
    BR
    CS
    HD

"""

#----------------------------------------------------------------------
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
logFile = file("ParsedThesaurus.log", "w")

#----------------------------------------------------------------------
# For serialization to XML.
#----------------------------------------------------------------------
def fix(s):
    return xml.sax.saxutils.escape(s)

class Concept:
    def __init__(self):
        self.code            = None
        self.kind            = None
        self.preferredName   = None
        self.fullSyn         = []
        self.definitions     = []
        self.indCodes        = []
        self.nscCodes        = []
        self.casCodes        = []
        self.editorNotes     = []
        self.needsReview     = False
    def toXml(self):
        if len(self.indCodes) > 1:
            logFile.write("multiple IND codes for %s\n" % self.code)
        if len(self.nscCodes) > 1:
            logFile.write("multiple NSC codes for %s\n" % self.code)
        if len(self.casCodes) > 1:
            logFile.write("multiple CAS codes for %s\n" % self.code)
        rep = u"<Concept code=%s>\n" % xml.sax.saxutils.quoteattr(self.code)
        if self.preferredName:
            preferredName = fix(self.preferredName)
            rep += u"<PreferredName>%s</PreferredName>\n" % preferredName
        if self.kind:
            rep += u"<Kind>%s</Kind>\n" % fix(self.kind)
        for fullSyn in self.fullSyn:
            rep += fullSyn.toXml()
        for definition in self.definitions:
            rep += definition.toXml()
        for indCode in self.indCodes:
            rep += u"<IndCode>%s</IndCode>\n" % fix(indCode)
        for nscCode in self.nscCodes:
            rep += u"<NscCode>%s</NscCode>\n" % fix(nscCode)
        for casCode in self.casCodes:
            rep += u"<CasCode>%s</CasCode>\n" % fix(casCode)
        return rep + u"</Concept>\n"

class Definition:
    pattern = re.compile(u"(<def-source>(.*)</def-source>)?"
                         u"(<def-definition>(.*)</def-definition>)?",
                         re.DOTALL)
    def __init__(self, value):
        match = Definition.pattern.search(value)
        self.source = None
        self.text   = None
        if match:
            self.source = match.group(2)
            self.text   = match.group(4)
    def toXml(self):
        src = xml.sax.saxutils.quoteattr(self.source)
        txt = fix(self.text)
        return u"<Definition source=%s>%s</Definition>\n" % (src, txt)

class FullSynonym:
    pattern = re.compile(u"(<term-name>(.*)</term-name>)?"
                         u"(<term-group>(.*)</term-group>)?"
                         u"(<term-source>(.*)</term-source>)?"
                         u"(<source-code>(.*)</source-code>)?",
                         re.DOTALL)
    def __init__(self, value):
        match = FullSynonym.pattern.search(value)
        self.termName   = None
        self.termGroup  = None
        self.termSource = None
        self.sourceCode = None
        if match:
            self.termName   = match.group(2)
            self.termGroup  = match.group(4)
            self.termSource = match.group(6)
            self.sourceCode = match.group(8)
    def toXml(self):
        src = xml.sax.saxutils.quoteattr(self.termSource)
        rep = u"<FullSyn source=%s>\n" % src
        if self.termName:
            rep += u"<TermName>%s</TermName>\n" % fix(self.termName)
        if self.termGroup:
            rep += u"<TermGroup>%s</TermGroup>\n" % fix(self.termGroup)
        if self.sourceCode:
            rep += u"<SourceCode>%s</SourceCode>\n" % fix(self.sourceCode)
        return rep + u"</FullSyn>\n"

class Thesaurus(xml.sax.handler.ContentHandler):
    def __init__(self, targetCodes = None):
        self.targetCodes = targetCodes
    def startDocument(self):
        self.path = []
        self.numConcepts = 0
        self.textContent = u''
        self.terms = {}
    def startElement(self, name, attributes):
        self.path.append(name)
        self.textContent = u''
        if name == 'conceptDef':
            self.concept = Concept()
    def endElement(self, name):
        self.path.pop()
        if name == 'conceptDef':
            self.numConcepts += 1
            if self.numConcepts % 100 == 0:
                sys.stderr.write("\r%d concepts parsed" % self.numConcepts)
            if self.concept.code:
                key = self.concept.code.upper()
                if self.targetCodes is None or key in self.targetCodes:
                    self.terms[key] = self.concept
        elif name == 'code' and self.path[-1] == 'conceptDef':
            if self.concept.code:
                logFile.write("multiple codes (%s, %s) for the same concept\n"
                              % (self.concept.code, self.textContent))
            else:
                self.concept.code = self.textContent.strip()
        elif name == 'name':
            if self.path[-1] == 'property':
                self.propertyName = self.textContent
        elif name == 'kind':
            if self.path[-1] == 'conceptDef':
                if self.concept.kind:
                    logFile.write("%s has multiple kinds\n" %
                                  self.concept.code)
                else:
                    self.concept.kind = self.textContent
        elif name == 'value' and self.path[-1] == 'property':
            if self.propertyName == 'Preferred_Name':
                if self.concept.preferredName:
                    logFile.write("%s has two preferred names\n" %
                                  self.concept.code)
                else:
                    self.concept.preferredName = self.textContent
            elif self.propertyName == 'FULL_SYN':
                fullSyn = FullSynonym(self.textContent)
                if fullSyn.termSource in ('NCI', 'NCI-GLOSS'):
                    self.concept.fullSyn.append(fullSyn)
            elif self.propertyName == 'DEFINITION':
                definition = Definition(self.textContent)
                if definition.source == 'NCI':
                    self.concept.definitions.append(definition)
            elif self.propertyName == 'IND_Code':
                self.concept.indCodes.append(self.textContent)
            elif self.propertyName == 'NSC_Code':
                self.concept.nscCodes.append(self.textContent)
            elif self.propertyName == 'CAS_Registry':
                self.concept.casCodes.append(self.textContent)
            elif self.propertyName == 'Editor_Note':
                self.concept.editorNotes.append(self.textContent)
                if u"DEFINITION NEEDS REVIEW" in self.textContent.upper():
                    self.concept.needsReview = True
                
    def characters(self, content):
        self.textContent += content
    def toXml(self):
        lines = ["<?xml version='1.0' encoding='utf-8' ?>",
                 "<Concepts>"]
        for code in self.terms:
            concept = self.terms[code]
            lines.append(concept.toXml().encode('utf-8'))
        lines.append("</Concepts>")
        return "\n".join(lines) + "\n"

#----------------------------------------------------------------------
# Test driver.
#----------------------------------------------------------------------
def main():
    book        = ExcelReader.Workbook('drug-terms.xls')
    sheet       = book[0]
    targetCodes = {}
    for row in sheet:
        if row.number > 0:
            code = str(row[1]).strip().upper()
            targetCodes[code] = True
    sys.stderr.write("%d target codes collected\n" % len(targetCodes))
    logFile.write("%d target codes collected\n" % len(targetCodes))
    thesaurus = Thesaurus(targetCodes)
    xml.sax.parse(sys.argv[1], thesaurus)
    sys.stderr.write("\r%d concepts parsed\n" % thesaurus.numConcepts)
    sys.stderr.write("%d target concepts collected\n" % len(thesaurus.terms))
    logFile.write("%d concepts parsed\n" % thesaurus.numConcepts)
    logFile.write("%d target concepts collected\n" % len(thesaurus.terms))
    print
    sys.stdout.write(thesaurus.toXml())

if __name__ == "__main__":
    main()
