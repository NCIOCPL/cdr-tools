#----------------------------------------------------------------------
#
# $Id: ReimportCitations.py,v 1.1 2003-03-11 14:50:48 bkline Exp $
#
# Second step in process to refresh citations invalidated by NLM DTD
# changes.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import glob, cdr, sys, re, os

#----------------------------------------------------------------------
# Parse out the errors for display.
#----------------------------------------------------------------------
def formatErrors(str):
    result = ""
    for error in re.findall("<Err>(.*?)</Err>", str):
        result += "%s\n" % error
    return result

if len(sys.argv) != 5:
    sys.stderr.write("usage: ReimportCitations uid pwd newdir olddir\n")
    sys.exit(1)
uid, pwd, dir, olddir = sys.argv[1:]
pattern1 = re.compile(r"%s.(\d+)\.xml" % dir)
pattern2 = re.compile("<PubmedArticle>.*?</PubmedArticle>", re.DOTALL)
pattern3 = re.compile("<ArticleTitle>(.*?)</ArticleTitle>", re.DOTALL)
session  = cdr.login(uid, pwd)
why      = "Re-imported citation from Pubmed because of NLM DTD changes"
if session.find("<Err") != -1:
    sys.stderr.write("failure logging in\n")
    sys.exit(1)
fileNames = glob.glob("%s/*.xml" % dir)
log = open("ReimportCitations.log", "w")
log.write("re-importing %d citations\n" % len(fileNames))
for fileName in fileNames:
    match = pattern1.search(fileName)
    if not match:
        sys.stderr.write("internal error: bad pattern %s\n" % fileName)
        sys.exit(1)
    id = int(match.group(1))
    sys.stderr.write("updating citation %d\n" % id)
    oldDoc = cdr.getDoc(session, id, 'Y')
    if oldDoc.startswith("<Errors"):
        cdrcgi.bail("Unable to retrieve %s" % replaceID)
    if not pattern2.findall(oldDoc):
        log.write("Document %d is not a PubMed Citation\n" % id)
        continue
    file = open("%s/%d.xml" % (olddir, id), "wb")
    file.write(oldDoc)
    file.close()
    file = open(fileName, "rb")
    article = pattern2.findall(file.read())
    file.close()
    if not article:
        log.write("can't find PubmedArticle in %s\n" % fileName)
        continue
    doc = pattern2.sub(article[0], oldDoc)
    resp = cdr.repDoc(session, doc = doc, val = 'Y', showWarnings = 1,
                      ver = 'Y', checkIn = 'Y', reason = why, comment = why)
    if not resp[0]:
        log.write("Failure replacing citation %d: %s\n" %
                  (id, cdr.checkErr(resp[1])))
        continue
    if not resp[1]:
        pubVerNote = "(with publishable version)"
        valErrors = ""
    else:
        pubVerNote = "(with validation errors)"
        valErrors = formatErrors(resp[1])
    log.write("Citation %s updated %s\n" % (resp[0], pubVerNote))
    if valErrors:
        log.write(valErrors)

cdr.logout(session)
