#----------------------------------------------------------------------
#
# $id: $
#
# Revalidates documents with missing link definition installed.
#
#----------------------------------------------------------------------
import cdr, re, sys, time

# 2003-04-15 11:42:17: Warnings for CDR0000038909: <Errors>

#----------------------------------------------------------------------
# Log processing/error information with a timestamp.
#----------------------------------------------------------------------
def log(what):
    what = "%s: %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), what)
    logFile.write(what)
    sys.stderr.write(what)
    
def saveDoc(id, doc, verPublishable, checkIn):
    log("saveDoc(%d, pub='%s', checkIn='%s')" % (id, verPublishable, checkIn))
    #return 1
    comment = "Revalidating Term document with link definition in place"
    response = cdr.repDoc(session, doc = doc, ver = 'Y', val = 'Y',
                          verPublishable = verPublishable, checkIn = checkIn,
                          reason = comment, comment = comment,
                          showWarnings = 'Y')
    if not response[0]:
        log("Failure versioning latest changes for CDR%010d: %s" %
            (id, response[1]))
        return 0
    if response[1]:
        log("Warnings for CDR%010d: %s" % (id, response[1]))
    return 1

logFile = open("FixInvalidCites.log", "a")
pattern = re.compile(r"Warnings for CDR0*(\d+): <Errors>")
session = cdr.login(sys.argv[1], sys.argv[2])
for line in sys.stdin:
    match = pattern.search(line)
    if match:
        digits = re.sub(r"[^\d]", "", match.group(1))
        id = int(digits)
        log("fixing CDR%010d" % id)
        resp = cdr.getDoc(session, id, 'Y')
        if resp.startswith("<Err"):
            log("Failure checking out CDR%010d: %s" % (self.id, cwd))
        else:
            saveDoc(id, resp, 'Y', 'Y')
