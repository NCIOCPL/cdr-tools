#----------------------------------------------------------------------
# $Id$
#
# Tool for generating script to drive get-prod-scripts.py.
#
# To use this:
#  1. mkdir prod-20150106
#  2. cd prod-20150106
#  3. python ../get-prod-scripts.py > get-prod-files.cmd
#  4. get-prod-files.cmd
#----------------------------------------------------------------------
import re, urllib2

BASE = "https://cdr.cancer.gov/cgi-bin/cdr/log-tail.py"
DIRS = ("cdr/Bin", "cdr/ClientFiles", "cdr/Database", "cdr/etc", "cdr/Lib",
        "cdr/Licensee", "cdr/Mailers", "cdr/Publishing", "cdr/Utilities",
        "etc", "Inetpub/wwwroot")

def unwanted(path):
    p = path.lower()
    if p.endswith(r"\cvs"):
        return True
    if p.startswith(r"d:\cdr\mailers\output"):
        return True
    if p.startswith(r"d:\cdr\utilities\ctgovdownloads"):
        return True
    if p.startswith(r"d:\cdr\utilities\bin\ctrpdownloads"):
        return True
    return False

for d in DIRS:
    path = d.replace("/", "\\")
    request = urllib2.urlopen("%s?p=d:\\%s\\*/s/ad" % (BASE, path))
    for line in request.read().splitlines():
        match = re.search("Directory of (d:.+)", line.strip())
        if match:
            p = match.group(1)
            if not unwanted(p):
                print 'python ../get-prod-scripts.py "%s" "%s"' % (p, p[3:])
