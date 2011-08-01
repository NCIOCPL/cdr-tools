#!/usr/bin/python
#----------------------------------------------------------------------
#
# $Id$
#
# Script used to test preliminary deliverables from Vanessa for
# task #4926.
#
# BZIssue::4926
#
#----------------------------------------------------------------------

import zipfile, xlrd, sys, MP3Info, cStringIO

MISSING = u"<span class='error'>FILE NOT FOUND</span>"
CORRUPT = u"<span class='error'>MP3 FILE CORRUPT</span>"

def getRuntime(bytes):
    if not bytes:
        return None
    try:
        fp = cStringIO.StringIO(bytes)
        mp3 = MP3Info.MPEG(fp)
        return mp3.length
    except:
        return None

class Pronunciation:
    def __init__(self, zipName, zipFile, sheet, row):
        self.zipName = zipName
        self.cdrId = int(sheet.cell(row, 0).value)
        self.termName = sheet.cell(row, 1).value
        self.language = sheet.cell(row, 2).value
        self.fileName = sheet.cell(row, 4).value
        try:
            self.bytes = zipFile.read(self.fileName)
            self.seconds = getRuntime(self.bytes)
        except:
            self.bytes = self.seconds = None

def collectInfo(zipNames):
    docs = {}
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
                        pronunciation = Pronunciation(zipName, zipFile,
                                                      sheet, row)
                    except Exception, e:
                        sys.stderr.write("%s: %s\n" % (sheet.cell(row, 0).value,
                                                       e))
                        continue
                    lowerName = pronunciation.fileName.lower()
                    if lowerName in fileNames:
                        sys.stderr.write("multiple %s in %s\n" %
                                         (lowerName, zipName))
                    else:
                        fileNames.add(lowerName)
                    key = (pronunciation.cdrId,
                           pronunciation.termName,
                           pronunciation.language)
                    if key in termNames:
                        sys.stderr.write("multiple %s in %s\n" %
                                         (repr(key), zipName))
                    else:
                        termNames.add(key)
                    doc = docs.get(pronunciation.cdrId)
                    if doc is None:
                        doc = docs[pronunciation.cdrId] = {}
                    termName = doc.get(pronunciation.termName)
                    if termName is None:
                        termName = doc[pronunciation.termName] = {}
                    language = termName.get(pronunciation.language)
                    if language is None:
                        language = termName[pronunciation.language] = []
                    language.append(pronunciation)
                break
    return docs

def makeHtmlReport(docs):
    html = [u"""\
<html>
 <head>
  <meta http-equiv='Content-Type' content='text/html;charset=utf-8' />
  <style type='text/css'>
   * { font-family: Arial, sans-serif; font-size: 10pt; }
   .error { color: red; }
  </style>
 </head>
 <body>
  <table border='1' cellpadding='2' cellspacing='0'>
   <tr>
    <th>CDR ID</th>
    <th>Term Name</th>
    <th>Language</th>
    <th>Set Name</th>
    <th>File Name</th>
    <th>Bytes</th>
    <th>Duration</th>
    <th>Notes</th>
"""]
    cdrIds = docs.keys()
    cdrIds.sort()
    for cdrId in cdrIds:
        termNames = docs[cdrId]
        nameKeys = termNames.keys()
        nameKeys.sort()
        for nameKey in nameKeys:
            languages = termNames[nameKey]
            languageKeys = languages.keys()
            languageKeys.sort()
            for languageKey in languageKeys:
                latest = languages[languageKey][-1]
                duration = byteCount = u"&nbsp;"
                notes = []
                if not latest.bytes:
                    notes = [MISSING]
                else:
                    byteCount = len(latest.bytes)
                    if latest.seconds is None:
                        notes = [CORRUPT]
                    else:
                        duration = u"00:%02d" % latest.seconds
                older = languages[languageKey][:-1]
                older.reverse()
                for o in older:
                    if o.bytes and o.bytes == latest.bytes:
                        continue
                    length = 0
                    if o.bytes:
                        length = len(o.bytes)
                    notes.append(u"overrides %d-byte %s from %s" %
                                 (length, o.fileName, o.zipName))
                html.append(u"""\
   <tr>
    <td valign='top'>CDR%d</td>
    <td valign='top'>%s</td>
    <td valign='top'>%s</td>
    <td valign='top'>%s</td>
    <td valign='top'>%s</td>
    <td valign='top' align='right'>%s</td>
    <td valign='top' align='center'>%s</td>
    <td valign='top'>%s</td>
   </tr>
""" % (cdrId, nameKey, languageKey, latest.zipName, latest.fileName,
       byteCount, duration, u"; ".join(notes) or u"&nbsp;"))
    html.append(u"""\
  </table>
 </body>
</html>
""")
    return u"".join(html)

def makeTextReport(docs):
    cdrIds = docs.keys()
    cdrIds.sort()
    for cdrId in cdrIds:
        termNames = docs[cdrId]
        nameKeys = termNames.keys()
        nameKeys.sort()
        for nameKey in nameKeys:
            languages = termNames[nameKey]
            languageKeys = languages.keys()
            languageKeys.sort()
            for languageKey in languageKeys:
                prefix = u"CDR%d: %s (%s):" % (cdrId, nameKey, languageKey)
                print prefix.encode('utf-8'),
                latest = languages[languageKey][-1]
                result = ["using %s from %s (%d bytes)" %
                          (latest.fileName, latest.zipName, len(latest.bytes))]
                for p in languages[languageKey][:-1]:
                    if p.bytes == latest.bytes:
                        result.append("identical with %s from %s" %
                                      (p.fileName, p.zipName))
                    else:
                        result.append("overrides %d-byte %s from %s" %
                                      (len(p.bytes), p.fileName, p.zipName))
                print "; ".join(result)


docs = collectInfo(sys.argv[1:])
print makeHtmlReport(docs).encode('utf-8')
