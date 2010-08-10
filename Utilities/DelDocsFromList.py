import cdr, glob, re, sys

if len(sys.argv) < 4:
    sys.stderr.write("usage: DelDocsFromList.py user password file [...]\n")
    sys.exit(1)
sess = cdr.login(sys.argv[1], sys.argv[2])
logFile = open("DelDocsFromList.log", "a")
pattern = re.compile(r'\s*(CDR)?(\d+)\s*')
for arg in sys.argv[3:]:
    for fileName in glob.glob(arg):
        logFile.write("*** DELETING DOCUMENTS FROM %s ***\n" % fileName)
        try:
            file = open(fileName)
        except Exception, info:
            logFile.write("### Failure opening %s: %s\n" % (fileName,
                                                            str(info)))
            continue
        for line in file:
            match = pattern.match(line)
            if match:
                id = int(match.group(2))
                resp = cdr.delDoc(sess, "CDR%010d" % id)
                logFile.write("%s\n" % resp)
                print resp
cdr.logout(sess)
