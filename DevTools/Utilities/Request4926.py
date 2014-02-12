#----------------------------------------------------------------------
#
# $Id$
#
# Add and link to glossary pronunciation Media documents.
#
# Invoke with command-line arguments identifying zip files containing
# media files to be added and accompanying spreadsheet telling how to
# link the new media documents from the appropriate GlossaryTermName
# documents.  The zip files must be named in the proper order, as
# media files found in zip files named later in the list of command
# line arguments will supercede those found in zip files named earlier.
# e.g.:
#    SET AUDIO=d:/cdr/Audio_from_CIPSFTP
#    Request4926.py rmk pw %AUDIO%/Week_026.zip %AUDIO%/Week_026_Rev1.zip
#
# BZIssue::4926
#
#----------------------------------------------------------------------
import xlrd, ModifyDocs, cdr, sys, lxml.etree as etree, cdrdb, os, cgi, MP3Info
import zipfile, cStringIO

CDRNS = "cips.nci.nih.gov/cdr"
NSMAP = { "cdr" : CDRNS }
LOGFILE = "%s/Request4926.log" % cdr.DEFAULT_LOGDIR

def log(me):
    sys.stderr.write("%s\n" % me)
    cdr.logwrite(me, LOGFILE)

def getCreationDate(path, zipFile):
    info = zipFile.getinfo(path)
    return "%04d-%02d-%02d" % info.date_time[:3]

def getRuntime(bytes):
    fp = cStringIO.StringIO(bytes)
    mp3 = MP3Info.MPEG(fp)
    return mp3.length

def getDocTitle(docId):
    cursor.execute("SELECT title FROM document WHERE id = ?", docId)
    return cursor.fetchall()[0][0]

def getCellValue(sheet, row, col):
    try:
        cell = sheet.cell(row, col)
        return cell and cell.value or None
    except:
        return None

class MP3:
    def __init__(self, zipName, zipFile, sheet, row):
        try:
            self.zipName = zipName
            self.nameId = int(getCellValue(sheet, row, 0))
        except Exception, e:
            log("%s row %s: %s" % (zipName, row, e))
            raise
        try:
            self.name = getCellValue(sheet, row, 1)
        except Exception, e:
            log("CDR%d row %s in %s: %s" % (self.nameId, row, zipName, e))
            raise
        try:
            self.language = getCellValue(sheet, row, 2)
            self.filename = getCellValue(sheet, row, 4)
            self.creator = getCellValue(sheet, row, 5)
            self.notes = getCellValue(sheet, row, 6)
            self.nameTitle = getDocTitle(self.nameId)
            self.bytes = zipFile.read(self.filename)
            self.duration = getRuntime(self.bytes)
            self.created = getCreationDate(self.filename, zipFile)
            self.title = self.nameTitle.split(';')[0]
            if self.language == 'Spanish':
                self.title += u"-Spanish"
            if self.language not in ('English', 'Spanish'):
                raise Exception("unexpected language value '%s'" %
                                self.language)
        except Exception, e:
            log("CDR%d %s (%s) row %s in %s: %s" %
                (self.nameId, repr(self.name), self.language, row, zipName, e))
            raise
    def makeElement(self):
        element = etree.Element('MediaLink')
        child = etree.Element('MediaID')
        child.text = u"%s; pronunciation; mp3" % self.title
        child.set("{cips.nci.nih.gov/cdr}ref", "CDR%010d" % self.mediaId)
        element.append(child)
        return element
    def findNameNode(self, tree):
        targetNode = None
        tag = self.language == 'English' and 'TermName' or 'TranslatedName'
        for node in tree.findall(tag):
            nameNode = NameNode(node)
            if nameNode.name == self.name:
                return nameNode
        raise Exception("unable to find name node for %s in CDR%s" %
                        (repr(self.name), self.nameId))
    def toXml(self):
        language = self.language == 'Spanish' and 'es' or 'en'
        creator = self.creator or u'Vanessa Richardson, VR Voice'
        root = etree.Element("Media", nsmap=NSMAP)
        root.set("Usage", "External")
        etree.SubElement(root, "MediaTitle").text = self.title
        physicalMedia = etree.SubElement(root, "PhysicalMedia")
        soundData = etree.SubElement(physicalMedia, "SoundData")
        etree.SubElement(soundData, "SoundType").text = "Speech"
        etree.SubElement(soundData, "SoundEncoding").text = "MP3"
        etree.SubElement(soundData, "RunSeconds").text = str(self.duration)
        mediaSource = etree.SubElement(root, "MediaSource")
        originalSource = etree.SubElement(mediaSource, "OriginalSource")
        etree.SubElement(originalSource, "Creator").text = creator
        etree.SubElement(originalSource, "DateCreated").text = self.created
        etree.SubElement(originalSource, "SourceFilename").text = self.filename
        mediaContent = etree.SubElement(root, "MediaContent")
        categories = etree.SubElement(mediaContent, "Categories")
        etree.SubElement(categories, "Category").text = "pronunciation"
        descs = etree.SubElement(mediaContent, "ContentDescriptions")
        desc = etree.SubElement(descs, "ContentDescription")
        desc.text = 'Pronunciation of dictionary term "%s"' % self.name
        desc.set("audience", "Patients")
        desc.set("language", language)
        proposedUse = etree.SubElement(root, "ProposedUse")
        glossary = etree.SubElement(proposedUse, "Glossary")
        glossary.set("{%s}ref" % CDRNS, "CDR%010d" % self.nameId)
        glossary.text = self.nameTitle
        return etree.tostring(root, pretty_print=True)
    def save(self, session):
        comment = "document created for CDR task 4926"
        docTitle = u"%s; pronunciation; mp3" % self.title
        ctrl = { 'DocType': 'Media', 'DocTitle': docTitle.encode('utf-8') }
        doc = cdr.Doc(self.toXml(), 'Media', ctrl, self.bytes, encoding='utf-8')
        result = cdr.addDoc(session, doc=str(doc), comment=comment, val='Y',
                            reason=comment, ver='Y', verPublishable='Y')
        self.mediaId = cdr.exNormalize(result)[1]
        cdr.unlock(session, self.mediaId)
        return self.mediaId

class NameNode:
    def __init__(self, node):
        self.node = node
        self.name = None
        self.insertPosition = 0
        for child in node:
            if child.tag == 'TermNameString':
                self.name = child.text
                self.insertPosition += 1
            elif child.tag in ('TranslationResource', 'MediaLink',
                               'TermPronunciation', 'PronunciationResource'):
                self.insertPosition += 1

class Request4926:
    def __init__(self, docs):
        self.docs = docs
    def getDocIds(self):
        docIds = self.docs.keys()
        docIds.sort()
        return docIds
    def run(self, docObject):
        docId = cdr.exNormalize(docObject.id)[1]
        try:
            docXml = docObject.xml
            tree = etree.XML(docXml)
            mp3s = self.docs[docId]
            for mp3 in mp3s:
                node = mp3.findNameNode(tree)
                node.node.insert(node.insertPosition, mp3.makeElement())
            return etree.tostring(tree)
        except Exception, e:
            self.job.log("CDR%d: %s" % (docId, e))
            return docObject.xml

def collectInfo(zipNames):
    """
    Create a nested dictionary for all of the sound files found in all
    of the zipfiles identified on the command line.  The top level of
    the dictionary is indexed by the CDR ID for the GlossaryTermName
    document with which the sound file belongs.  Within a given
    GlossaryTermName document is a nested dictionary indexed by the
    term name string.  Because Spanish and English often spell the
    term name the same way, each entry in this dictionary is in turn
    another dictionary indexed by the name of the language.  Each entry
    in these dictionaries at the lowest level is a sequence of MP3 objects.
    Since the zipfiles are named on the command line in ascending order
    of precedence, the last MP3 object in a given sequence supercedes
    the earlier objects in that sequence.
    """
    nameDocs = {}
    for zipName in zipNames:
        zipFile = zipfile.ZipFile(zipName)
        fileNames = set()
        termNames = set()
        for name in zipFile.namelist():
            if "MACOSX" not in name and name.endswith(".xls"):
                xlBytes = zipFile.read(name)
                book = xlrd.open_workbook(file_contents=xlBytes)
                sheet = book.sheet_by_index(0)
                for row in range(sheet.nrows):
                    try:
                        mp3 = MP3(zipName, zipFile, sheet, row)
                    except Exception, e:
                        continue
                    lowerName = mp3.filename.lower()
                    if lowerName in fileNames:
                        log("multiple %s in %s" % (lowerName, zipName))
                    else:
                        fileNames.add(lowerName)
                    key = (mp3.nameId, mp3.name, mp3.language)
                    if key in termNames:
                        log("multiple %s in %s" % (repr(key), zipName))
                    else:
                        termNames.add(key)
                    nameDoc = nameDocs.get(mp3.nameId)
                    if nameDoc is None:
                        nameDoc = nameDocs[mp3.nameId] = {}
                    termName = nameDoc.get(mp3.name)
                    if termName is None:
                        termName = nameDoc[mp3.name] = {}
                    mp3sForThisLanguage = termName.get(mp3.language)
                    if mp3sForThisLanguage is None:
                        mp3sForThisLanguage = termName[mp3.language] = []
                    mp3sForThisLanguage.append(mp3)
                break
    return nameDocs

if len(sys.argv) < 4:
    sys.stderr.write(
        "usage: %s uid pwd zipfile [zipfile ...]\n" %
        sys.argv[0])
    sys.exit(1)
uid, pwd = sys.argv[1:3]
zipnames = sys.argv[3:]
session = cdr.login(uid, pwd)
cursor = cdrdb.connect('CdrGuest').cursor()
cursor.execute("""\
SELECT DISTINCT doc_id
           FROM query_term
          WHERE path LIKE '/GlossaryTermName/%/MediaLink/MediaID/@cdr:ref'""")
alreadyDone = set([row[0] for row in cursor.fetchall()])
print "%d documents already processed" % len(alreadyDone)
info = collectInfo(zipnames)
mediaDocs = {}
docs = {}
for nameId in info:
    if nameId in alreadyDone:
        log("skipping CDR%d: already done" % nameId)
        continue
    mp3sForNameDoc = []
    termNames = info[nameId]
    for termName in termNames:
        languages = termNames[termName]
        for language in languages:
            mp3s = languages[language]
            lang = language == 'Spanish' and 'es' or 'en'
            key = (nameId, termName, lang)
            mp3 = mp3s[-1]
            mp3sForNameDoc.append(mp3)
            mediaId = mediaDocs.get(key)
            if mediaId:
                log("%s already saved as CDR%d" % (repr(key), mediaId))
                mp3.mediaId = mediaId
            else:
                mediaId = mp3.save(session)
                mediaDocs[key] = mediaId
                log("saved %s from %s as CDR%d" % (key, mp3.zipName, mediaId))
    if mp3sForNameDoc:
        docs[nameId] = mp3sForNameDoc
obj = Request4926(docs)
job = ModifyDocs.Job(uid, pwd, obj, obj, "Request 4926", validate=True,
                     testMode=False, logFile=LOGFILE)
obj.job = job
job.run()
