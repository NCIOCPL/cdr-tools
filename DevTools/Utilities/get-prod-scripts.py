#----------------------------------------------------------------------
# $Id$
#
# Tool for pulling scripts from a production directory down to the
# local file system.  Doesn't recurse.  Doesn't handle binary files.
#----------------------------------------------------------------------
import re, sys, urllib2

#----------------------------------------------------------------------
# Replace encoded character with itself.
#----------------------------------------------------------------------
def unescape(match):
    return chr(int(match.group(0)[1:], 16))

#----------------------------------------------------------------------
# Strip extra lines added by log-tail.py, normalize space, and remove
# encoding.
#----------------------------------------------------------------------
def fix(me):
    return "\n".join(re.sub("%..", unescape, me).splitlines()[2:-1]) + "\n"

PATH = len(sys.argv) > 1 and sys.argv[1] or r"d:\Inetpub\wwwroot\cgi-bin\cdr"
BASE = "https://cdr.cancer.gov/cgi-bin/cdr/log-tail.py"
DIR  = len(sys.argv) > 2 and sys.argv[2] or "cgi-prod"

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
        request = urllib2.urlopen("%s?c=100000000&p=%s" % (BASE, path))
        script = request.read()
        fp = open("%s/%s" % (DIR, name), "wb")
        fp.write(fix(script))
        fp.close()
    except Exception, e:
        sys.stderr.write("\n%s: %s\n" % (path, e))
    done += 1
    sys.stderr.write("\rretrieved %d of %d" % (done, len(names)))
sys.stderr.write("\n")
