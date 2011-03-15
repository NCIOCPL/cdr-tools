#----------------------------------------------------------------------
#
# $Id$
#
# Add and link to glossary pronunciation Media documents.
#
# BZIssue::4926
#
#----------------------------------------------------------------------
import ExcelReader, ModifyDocs, cdr, sys, lxml.etree as etree, cdrdb, time, os
import MP3Info, cgi

def getCreationDate(path):
    s = os.stat(path)
    return time.strftime("%Y-%m-%d", time.localtime(s.st_mtime))

def getDuration(path):
    mp3 = MP3Info.MPEG(open(path, 'rb'))
    return mp3.length_seconds

def getDocTitle(docId):
    cursor.execute("SELECT title FROM document WHERE id = ?", docId)
    return cursor.fetchall()[0][0]

class MP3:
    def __init__(self, row):
        self.nameId = int(row[0].val)
        self.nameTitle = getDocTitle(self.nameId)
        self.name = row[1].val
        self.language = row[2].val
        self.filename = row[4].val
        self.creator = row[5] and row[5].val or None
        self.notes = row[6] and row[6].val or None
        self.fullPath = "%s/%s" % (basePath, self.filename)
        self.created = getCreationDate(self.fullPath)
        self.duration = getDuration(self.fullPath)
        if self.language not in ('English', 'Spanish'):
            raise Exception("unexpected language value '%s'" % self.language)
    def makeElement(self):
        element = etree.Element('MediaLink')
        child = etree.Element('MediaID')
        child.text = u"%s; pronunciation; mp3" % self.name
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
    def save(self, session):
        bytes = open(self.fullPath, 'rb').read()
        comment = "document created for CDR task 4926"
        language = self.language == 'Spanish' and 'es' or 'en'
        creator = self.creator or u'Vanessa Richardson, VR Voice'
        docTitle = u"%s; pronunciation; mp3" % self.name
        name = self.nameTitle.split(';')[0]
        title = name
        if self.language == 'Spanish':
            title += u"-Spanish"
        #ctrl = { 'DocType': 'Media', 'DocTitle': docTitle.encode('utf-8') }
        ctrl = { 'DocType': 'Media', 'DocTitle': title.encode('utf-8') }
        docXml = u"""\
<Media xmlns:cdr='cips.nci.nih.gov/cdr'>
 <MediaTitle>%s</MediaTitle>
 <PhysicalMedia>
  <SoundData>
   <SoundType>Speech</SoundType>
   <SoundEncoding>MP3</SoundEncoding>
   <RunSeconds>%s</RunSeconds>
  </SoundData>
 </PhysicalMedia>
 <MediaSource>
  <OriginalSource>
   <Creator>%s</Creator>
   <DateCreated>%s</DateCreated>
   <SourceFilename>%s</SourceFilename>
  </OriginalSource>
 </MediaSource>
 <MediaContent>
  <Categories>
   <Category>pronunciation</Category>
  </Categories>
  <ContentDescriptions>
   <ContentDescription audience='Patients' language='%s'>Pronunciation of dictionary term '%s'</ContentDescription>
  </ContentDescriptions>
 </MediaContent>
 <ProposedUse>
  <Glossary cdr:ref='CDR%010d'>%s</Glossary>
 </ProposedUse>
</Media>
""" % (cgi.escape(title), self.duration, cgi.escape(creator),
       self.created, self.filename, language, cgi.escape(self.name),
       self.nameId, cgi.escape(self.nameTitle))
        doc = cdr.Doc(docXml.encode('utf-8'), 'Media', ctrl, bytes,
                      encoding='utf-8')
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
        docXml = docObject.xml
        tree = etree.XML(docXml)
        mp3s = self.docs[docId]
        for mp3 in mp3s:
            node = mp3.findNameNode(tree)
            node.node.insert(node.insertPosition, mp3.makeElement())
        return etree.tostring(tree)

fp = open('media-docs.repr')
mediaDocs = {}
for line in fp:
    k, v = eval(line)
    mediaDocs[k] = v
fp.close()
if len(sys.argv) != 5:
    sys.stderr.write("usage: %s uid pwd spreadsheet basepath\n" % sys.argv[0])
    sys.exit(1)
uid, pwd, xls, basePath = sys.argv[1:]
session = cdr.login(uid, pwd)
docs = {}
cursor = cdrdb.connect('CdrGuest').cursor()
cursor.execute("""\
SELECT DISTINCT doc_id
           FROM query_term
          WHERE path LIKE '/GlossaryTermName/%/MediaLink/MediaID/@cdr:ref'""")
alreadyDone = set([row[0] for row in cursor.fetchall()])
print "%d documents already processed" % len(alreadyDone)
book = ExcelReader.Workbook(xls)
sheet = book[0]
for row in sheet:
    try:
        mp3 = MP3(row)
    except Exception, e:
        print "skipping %s: %s" % (row[0].val, e)
        continue
    if mp3.nameId in alreadyDone:
        print "skipping CDR%s: already done" % mp3.nameId
        continue
    if mp3.nameId in docs:
        docs[mp3.nameId].append(mp3)
    else:
        docs[mp3.nameId] = [mp3]
    lang = mp3.language == 'Spanish' and 'es' or 'en'
    key = (mp3.nameId, mp3.name, lang)
    mediaId = mediaDocs.get(key)
    if mediaId:
        print repr(key), "already saved as CDR doc", mediaId
        mp3.mediaId = mediaId
    else:
        mediaId = mp3.save(session)
        mediaDocs[key] = mediaId
        print "saved %s as CDR%d" % (key, mediaId)
        #break
fp = open('media-docs.repr', 'w')
for k, v in mediaDocs.iteritems():
    fp.write("%s\n" % repr((k, v)))
fp.close()
obj = Request4926(docs)
job = ModifyDocs.Job(uid, pwd, obj, obj, "Request 4926", validate=True,
                     testMode=False)
job.run()
