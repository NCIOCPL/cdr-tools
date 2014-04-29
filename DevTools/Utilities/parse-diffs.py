#----------------------------------------------------------------------
# $Id$
#
# Tool to parse diff output when comparing files on live prod directory
# with what's in Subversion.
#----------------------------------------------------------------------
import re, sys, os

for line in sys.stdin:
    line = line.strip()
    match = re.match("Only in prod[^:]+: (.*)", line)
    if match:
        print "%s\tP" % match.group(1)
        continue
    match = re.match("Only in svn[^:]+: (.*)", line)
    if match:
        print "%s\tS" % match.group(1)
        continue
    match = re.match("Files (prod.*) and svn.* differ", line)
    if match:
        print "%s\tD" % os.path.basename(match.group(1))
        continue
