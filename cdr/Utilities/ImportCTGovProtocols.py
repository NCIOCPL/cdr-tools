#----------------------------------------------------------------------
#
# $Id: ImportCTGovProtocols.py,v 1.1 2003-11-05 16:25:19 bkline Exp $
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdr, cdrdb, sys, xml.sax, re

class CTGovHandler(xml.sax.handler.ContentHandler):
    def __init__(self):
        self.doc    = u""
        self.para   = u""
        self.inPara = 0
    def startDocument(self):
        self.doc = u"<?xml version='1.0'?>\n"
    def startElement(self, name, attributes):
        if name == u'Para':
            self.para   = u""
            self.inPara = 1
        else:
            self.doc += u"<%s" % name
            for attrName in attributes.getNames():
                val = xml.sax.saxutils.quoteattr(attributes.getValue(attrName))
                self.doc += u" %s=%s" % (attrName, val)
            self.doc += u">"
    def endElement(self, name):
        if name == 'Para':
            self.doc += self.parsePara()
            self.inPara = 0
            self.para = u""
        else:
            self.doc += "</%s>" % name
    def characters(self, content):
        if self.inPara:
            self.para += xml.sax.saxutils.escape(content)
        else:
            self.doc += xml.sax.saxutils.escape(content)
    def processingInstruction(self, target, data):
        self.doc += "<?%s %s?>" % (target, data)
    def parsePara(self):
        self.para = self.para.strip()
        self.para = self.para.replace(u"\r", "")
        if not self.para:
            return u"<Para/>\n"
        result = u""
        chunks = re.split(u"\n\n+", self.para)
        for chunk in chunks:
            if re.match(r"\s+-\s", chunk):
                result += u"<ItemizedList>\n"
                for item in re.split(r"\n\s+-\s", u"dummy\n" + chunk)[1:]:
                    result += u"<ListItem>%s</ListItem>\n" % item.strip()
                result += u"</ItemizedList>\n"
            else:
                result += u"<Para>%s</Para>\n" % chunk.strip()
        return result

parser = CTGovHandler()
def parseParas(doc):
    parser.doc = u""
    xml.sax.parseString(doc, parser)
    return parser.doc

LOGFILE = cdr.DEFAULT_LOGDIR + "/CTGovImport.log"
def log(msg, cdrErrors = None):
    if cdrErrors:
        errors = cdr.getErrors(cdrErrors, asSequence = 1)
        if not errors:
            cdr.logwrite(msg, LOGFILE)
        elif len(errors) == 1:
            cdr.logwrite("%s: %s" % (msg, errors[0]), LOGFILE)
        else:
            cdr.logwrite(msg, LOGFILE)
            cdr.logwrite(errors, LOGFILE)
    else:
        cdr.logwrite(msg, LOGFILE)

def checkResponse(resp):
    if not resp[0]:
        errors = cdr.getErrors(resp[1], errorsExpected = 1, asSequence = 1)
        raise Exception(errors)

def extractDocSubset(cdrId, docVer = None):
    response = cdr.filter(session,
                          'name:Extract Significant CTGovProtocol Elements',
                          cdrId, docVer = docVer)
    if not response[0]:
        raise Exception(response[1])
    return response[0]

def hasMajorDiffs(cdrId, version, newSubset):
    oldSubset = extractDocSubset(cdrId, version)
    return newSubset != oldSubset
    
def mergeVersion(newDoc, cdrId, docObject, docVer):
    element  = ""
    response = cdr.getDoc('guest', cdrId, version = docVer)
    errors   = cdr.getErrors(response, errorsExpected = 0, asSequence = 1)
    if errors:
        raise Exception(errors)
    startTag = "<PDQIndexing"
    endTag   = "</PDQIndexing>"
    begin    = response.find(startTag)
    while begin != -1 and response[begin + len(startTag)] not in "> \n\r\t":
        begin = response.find(startTag, begin + 1)
    if begin != -1:
        end = response.find(endTag, begin)
        if end != -1:
            element = response[begin:end + len(endTag)]
    docObject.xml = newDoc.replace('@@PDQIndexing@@', element)
    return str(docObject)

def mergeChanges(cdrId, newDoc):

    whichSet = None
    response = cdr.getDoc(session, cdrId, checkout = 'Y')
    errors   = cdr.getErrors(response, errorsExpected = 0, asSequence = 1)
    if errors:
        lockedDocs[cdrId] = 1
        raise Exception(errors)
    docObject = response
    originalXml = docObject.xml
    response = cdr.filter(session,
                          'name:Extract Significant CTGovProtocol Elements',
                          doc = newDoc)
    if not response[0]:
        raise Exception(response[1])
    newSubset = response[0]
    lastAny, lastPub, isChanged = cdr.lastVersions(session, cdrId)

    # Save the old CWD as a version if appropriate.
    if isChanged == 'Y':
        comment = 'ImportCTGovProtocols: preserving current working doc'
        response = cdr.repDoc(session, doc = `docObject`, ver = 'Y',
                              comment = comment, reason = comment,
                              showWarnings = 1)
        checkResponse(response)


    # Has a publishable version ever been saved for this document?
    if lastPub != -1:

        # If the differences are not significant, create a new pub. ver.
        if hasMajorDiffs(cdrId, lastPub, newSubset):
            whichSet = needsReview
        else:
            newPubVer = mergeVersion(newDoc, cdrId, docObject, lastPub)
            comment = 'ImportCTGovProtocols: creating new publishable version'
            response = cdr.repDoc(session, doc = newPubVer, ver = 'Y',
                                  verPublishable = 'Y', val = 'Y',
                                  comment = comment, reason = comment,
                                  showWarnings = 1)
            checkResponse(response)
            whichSet = pubVersionsCreated

    else:

        if hasMajorDiffs(cdrId, None, newSubset):
            whichSet = needsReview
        
    # Create a new CWD from the one we found.
    newCwd   = mergeVersion(newDoc, cdrId, docObject, "Current")
    comment  = 'ImportCTGovProtocols: creating new CWD'
    response = cdr.repDoc(session, doc = newCwd,
                          comment = comment, reason = comment,
                          showWarnings = 1)
    checkResponse(response)

    # Remember what we did for the report.
    if whichSet:
        whichSet[cdrId] = 1

#----------------------------------------------------------------------
# Processing starts here.
#----------------------------------------------------------------------
conn               = cdrdb.connect()
cursor             = conn.cursor()
needsReview        = {}
pubVersionsCreated = {}
lockedDocs         = {}
session            = cdr.login(sys.argv[1], sys.argv[2])
errors             = cdr.getErrors(session, errorsExpected = 0, asSequence = 1)
if errors:
    cdr.logwrite("Login failure", session)
    sys.stderr.write("Login failure: %s" % str(errors))
    sys.exit(1)
cursor.execute("SELECT id FROM ctgov_disposition WHERE name = 'imported'")
importedDisposition = cursor.fetchall()[0][0]
cursor.execute("""\
    SELECT c.nlm_id, c.cdr_id
      FROM ctgov_import c
      JOIN ctgov_disposition d
        ON d.id = c.disposition
     WHERE d.name = 'import requested'""")
rows = cursor.fetchall()

for nlmId, cdrId in rows:
    cursor.execute("SELECT xml FROM ctgov_import WHERE nlm_id = ?", nlmId)
    doc = cursor.fetchone()[0]
    parms = [['newDoc', cdrId and 'N' or 'Y']]
    resp = cdr.filterDoc('guest', ['name:Import CTGovProtocol'], doc = doc,
                         parm = parms)
    if type(resp) in (type(""), type(u"")):
        log("Failure converting %s" % nlmId, resp)
        continue
    doc = parseParas(resp[0])

    #------------------------------------------------------------------
    # Add new doc.
    #------------------------------------------------------------------
    if not cdrId:
        comment = 'Adding imported CTGovProtocol document'
        resp = cdr.addDoc(session, doc = """\
<CdrDoc Type='CTGovProtocol'>
 <CdrDocCtl/>
 <CdrDocXml><![CDATA[%s]]></CdrDocXml>
</CdrDoc>
""" % doc.encode('utf-8'), showWarnings = 1, #comment = comment,
                          reason = comment)
        if not resp[0]:
            log("Failure adding %s" % nlmId, resp[1])
        else:
            print cdr.unlock(session, resp[0],
                             reason = 'Unlocking imported CTGovProtocol doc')
            digits = re.sub(r'[^\d]', '', resp[0])
            cdrId = int(digits)
            cursor.execute("""\
            UPDATE ctgov_import
               SET disposition = ?,
                   dt = GETDATE(),
                   cdr_id = ?
             WHERE nlm_id = ?""", (importedDisposition, cdrId, nlmId))
            conn.commit()
            log("Added %s as %s" % (nlmId, resp[0]))
            newDocs[cdrId] = 1

    #------------------------------------------------------------------
    # Merge changes into existing doc.
    #------------------------------------------------------------------
    else:
        try:
            comment = 'Merging changes into CTGovProtocol document'
            mergeChanges("CDR%d" % cdrId, doc)
            cursor.execute("""\
            UPDATE ctgov_import
               SET disposition = ?,
                   dt = GETDATE()
             WHERE nlm_id = ?""", (importedDisposition, nlmId))
            conn.commit()
        except Exception, info:
            log("Failure merging changes for %s into %s: %s" %
                (nlmId, cdrId, str(info)))
        cdr.unlock(session, "CDR%d" % cdrId,
                   reason = 'Unlocking updated CTGovProtocol doc')
