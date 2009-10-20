#----------------------------------------------------------------------
#
# $Id$
#
# Adjust the information of the OtherPublicationInformation element
# according to the schema changes as listed in Bug 1607 in order to
# split the information into the OtherInformation and InternetInformation
# elements.
#
# BZIssue::1829
#
#----------------------------------------------------------------------
import cdr, cdrdb, ModifyDocs, sys, re, xml.sax.handler

class OtherPublicationInformationHandler(xml.sax.handler.ContentHandler):
    
    def __init__(self):
        self.docStrings         = []
        self.inOPI              = False
        self.inOI               = False
        self.inII               = False
        self.oiStrings          = []
        self.iiStrings          = []
    
    def startDocument(self):
        self.docStrings         = [u"<?xml version='1.0'?>\n"]
        self.inOPI              = False
        self.inOI               = False
        self.inII               = False
        self.oiStrings          = []
        self.iiStrings          = []

    def startElement(self, name, attributes):
        dropCdrId = False
        docStrings = self.docStrings
        if name == u'OtherPublicationInformation':
            dropCdrId = True
            self.inOPI = True
            self.inOI = True
        elif self.inOPI:
            if name == u"ExternalRef":
                self.inII = True
                self.inOI = False
            if self.inOI:
                docStrings = self.oiStrings
            elif self.inII:
                docStrings = self.iiStrings
        docStrings.append(u"<%s" % name)
        for attrName in attributes.getNames():
            if attrName != u'cdr:id' or not dropCdrId:
                val = xml.sax.saxutils.quoteattr(attributes.getValue(attrName))
                docStrings.append(u" %s=%s" % (attrName, val))
        docStrings.append(u">")

    def __wrapStrings(self, name, strings):
        self.docStrings.append(u"<%s>" % name)
        self.docStrings.append(u"".join(strings).strip())
        self.docStrings.append(u"</%s>" % name)
        
    def endElement(self, name):
        if name == 'OtherPublicationInformation':
            self.__wrapStrings(u'PublicationInformation', self.oiStrings)
            self.oiStrings = []
            if self.iiStrings:
                self.__wrapStrings(u'InternetInformation', self.iiStrings)
                self.iiStrings = []
            self.inOPI = self.inOI = self.inII = False
        if self.inOI:
            docStrings = self.oiStrings
        elif self.inII:
            docStrings = self.iiStrings
        else:
            docStrings = self.docStrings
        docStrings.append(u"</%s>" % name)

    def characters(self, content):
        if self.inOI:
            docStrings = self.oiStrings
        elif self.inII:
            docStrings = self.iiStrings
        else:
            docStrings = self.docStrings
        docStrings.append(xml.sax.saxutils.escape(content))

    def processingInstruction(self, target, data):
        if self.inOI:
            docStrings = self.oiStrings
        elif self.inII:
            docStrings = self.iiStrings
        else:
            docStrings = self.docStrings
        docStrings.append(u"<?%s %s?>" % (target, data))

#----------------------------------------------------------------------
# The Filter class is given to the ModifyDocs.Job object, which invokes
# the getDocIds() method to retrieve a list of CDR document IDs for
# processing.
#----------------------------------------------------------------------
class Filter:
    def getDocIds(self):
        conn = cdrdb.connect('CdrGuest')
        cursor = conn.cursor()
        cursor.execute("""\
    SELECT DISTINCT doc_id
               FROM query_term
              WHERE path = '/Citation/PDQCitation/PublicationDetails'
                         + '/OtherPublicationInformation/@cdr:id'
           ORDER BY doc_id""")
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
        self.parser = OtherPublicationInformationHandler()
    def run(self, docObj):
        xml.sax.parseString(docObj.xml, self.parser)
        return u"".join(self.parser.docStrings).encode('utf-8')

if len(sys.argv) < 4 or sys.argv[3] not in ('test', 'live'):
    sys.stderr.write("usage: Request1829.py uid pwd test|live\n")
    sys.exit(1)
testMode = sys.argv[3] == 'test'
job = ModifyDocs.Job(sys.argv[1], sys.argv[2], Filter(), Transform(),
                     "Split OtherPublicationInformation elements "
                     "(request #1829).",
                     testMode = testMode)
job.run()
