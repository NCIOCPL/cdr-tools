#----------------------------------------------------------------------
# $Id$
#
# Tool for pulling scripts from a production directory down to the
# local file system.  Doesn't recurse.  Handles binary files.
#----------------------------------------------------------------------
import os, re, sys, urllib2

PATH = len(sys.argv) > 1 and sys.argv[1] or r"d:\Inetpub\wwwroot\cgi-bin\cdr"
BASE = "https://cdr.cancer.gov/cgi-bin/cdr/log-tail.py"
DIR  = len(sys.argv) > 2 and sys.argv[2] or "cgi-prod"

try:
    os.makedirs(DIR)
    sys.stderr.write("created %s\n" % DIR)
except:
    sys.stderr.write("%s already created\n" % DIR)

request = urllib2.urlopen("%s?p=%s\\*" % (BASE, PATH))
names = []
for line in request.read().splitlines():
    pieces = re.split("\\s+", line.strip(), 4)
    if len(pieces) == 5 and pieces[2] in ("AM", "PM") and pieces[3] != "<DIR>":
        names.append(pieces[4])
done = 0
for name in sorted(names):
    path = "%s\\%s" % (PATH, name.replace(" ", "+"))
    try:
        request = urllib2.urlopen("%s?r=1&p=%s" % (BASE, path))
        script = request.read()
        fp = open("%s/%s" % (DIR, name), "wb")
        fp.write(script)
        fp.close()
    except Exception, e:
        fp = open("get-prod-scripts.err", "a")
        fp.write("%s: %s\n" % (path, e))
        fp.close()
        sys.stderr.write("\n%s: %s\n" % (path, e))
    done += 1
    sys.stderr.write("\rretrieved %d of %d" % (done, len(names)))
sys.stderr.write("\n")
