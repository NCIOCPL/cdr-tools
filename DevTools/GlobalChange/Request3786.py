#----------------------------------------------------------------------
#
# $Id$
#
# One-off to insert the Safety attribute for Outcome elements.
#
# "We need a one-off global that will insert the new Safety (Yes/No) attribute
# in InScopeProtocol documents.
#
# This global will be for InScope Protocols:
#     Study Type = Clinical trial
#     Study Category Type = Primary
#
# Do not include:
#     Study Category Name - Supportive care, Natural history/Epidemiology
#     (The global would be assigning safety to something that is more efficacy
#     or long-term effect of therapy if we included these. CIAT will assign
#     Safety manually to these).
#
# The global will assign the Safety attribute = Yes to the <Outcome> elements
# that have the following words or text strings (case insensitive):
#
#    safety
#    adverse
#    toxic
#    toxicity
#    toxicities
#    side effect
#    side-effect
#    tolerance
#    tolerability
#    Maximum tolerated dose
#    MTD
#    Recommended phase II dos
#
# The attribute for the trials that do not have these words/text strings will
# be set to Safety = No."
#
# BZIssue::3786
#
#----------------------------------------------------------------------
import cdrdb, sys, ModifyDocs, xml.sax.handler, xml.sax.saxutils

#----------------------------------------------------------------------
# Escape special characters in an XML string.
#----------------------------------------------------------------------
def fix(xmlString):
    return xmlString and xml.sax.saxutils.escape(xmlString) or u""

#----------------------------------------------------------------------
# Extracts OtherTermName objects from CDR Term documents.
#----------------------------------------------------------------------
class Parser(xml.sax.handler.ContentHandler):

    def __init__(self):
        self.docStrings         = []
        self.outcomeText        = []
        self.inOutcome          = False
    
    def startDocument(self):
        self.docStrings         = [u"<?xml version='1.0'?>\n"]
        self.outcomeText        = []
        self.inOutcome          = False

    def startElement(self, name, attributes):
        if self.inOutcome:
            raise Exception("markup (%s) found inside Outcome element" % name)
        if name == 'Outcome':
            self.inOutcome = True
        self.docStrings.append(u"<%s" % name)
        for attrName in attributes.getNames():
            if self.inOutcome and attrName == 'Safety':
                raise Exception("Safety attribute already present")
            val = xml.sax.saxutils.quoteattr(attributes.getValue(attrName))
            self.docStrings.append(u" %s=%s" % (attrName, val))
        if not self.inOutcome:
            self.docStrings.append(u">")

    def __getSafety(self):
        t = self.outcomeText.lower()
        for w in (u'safety', u'adverse', u'toxic', u'toxicity', u'toxicities',
                  u'side effect', u'side-effect', u'tolerance',
                  u'tolerability', u'maximum tolerated dose', u'mtd',
                  u'recommended phase ii dose'):
            if w in t:
                return u"Yes"
        return u"No"

    def endElement(self, name):
        if self.inOutcome:
            self.outcomeText = u"".join(self.outcomeText)
            self.docStrings.append(u' Safety="%s">%s</Outcome>' %
                                   (self.__getSafety(), fix(self.outcomeText)))
            self.inOutcome = False
            self.outcomeText = []
        elif name == 'Outcome':
            raise Exception("dryrot! end tag for Outcome unexpected")
        else:
            self.docStrings.append(u"</%s>" % name)

    def characters(self, content):
        if self.inOutcome:
            self.outcomeText.append(content)
        else:
            self.docStrings.append(fix(content))

    def processingInstruction(self, target, data):
        if self.inOutcome:
            raise Exception("found %s PI inside Outcome element" % target)
        else:
            self.docStrings.append(u"<?%s %s?>" % (target, data))

#----------------------------------------------------------------------
# The Filter class is given to the ModifyDocs.Job object, which invokes
# the getDocIds() method to retrieve a list of CDR document IDs for
# processing.
#----------------------------------------------------------------------
class Filter:
    def getDocIds(self):
        cursor = cdrdb.connect('CdrGuest').cursor()
        cursor.execute("""\
  SELECT DISTINCT doc_id
    FROM query_term
   WHERE path = '/InScopeProtocol/ProtocolDetail/StudyType'
     AND value = 'Clinical trial'
     AND doc_id NOT IN (SELECT DISTINCT c.doc_id
                          FROM query_term c
                          JOIN query_term t
                            ON c.doc_id = t.doc_id
                           AND LEFT(c.node_loc, 8) = LEFT(t.node_loc, 8)
                         WHERE t.value = 'Primary'
                           AND t.path = '/InScopeProtocol/ProtocolDetail'
                                      + '/StudyCategory/StudyCategoryType'
                           AND c.path = '/InScopeProtocol/ProtocolDetail'
                                      + '/StudyCategory/StudyCategoryName'
                           AND c.value IN ('Supportive care',
                                           'Natural history/Epidemiology'))""")
        return [row[0] for row in cursor.fetchall()]

#----------------------------------------------------------------------
# The Transform class is given to the ModifyDocs.Job object, which in
# turn gives it to each ModifyDocs.Doc object.  The run() method of
# this class takes a cdr.Doc object and returns a (possibly) modified
# copy of that object's xml member.
#
# See comment at top for this job's logic.
#----------------------------------------------------------------------
class Transform:
    def __init__(self):
        self.parser = Parser()

    def run(self, docObj):
        xml.sax.parseString(docObj.xml, self.parser)
        return u"".join(self.parser.docStrings).encode('utf-8')

#----------------------------------------------------------------------
# Processing starts here.
#----------------------------------------------------------------------
if len(sys.argv) < 3:
    sys.stderr.write("usage: %s uid pwd [LIVE|max-docs]\n" % sys.argv[0])
    sys.exit(1)

testMode = len(sys.argv) < 4 or sys.argv[3] != "LIVE"
job      = ModifyDocs.Job(sys.argv[1], sys.argv[2], Filter(), Transform(),
                          "Adding Safety attributes (request #3786).",
                          testMode = testMode)
if testMode and len(sys.argv) > 3:
    job.setMaxDocs(int(sys.argv[3]))
job.run()
