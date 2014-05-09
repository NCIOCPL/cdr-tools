import re
for line in open("cdr-lib.diff"):
    line = line.strip()
    match = re.match("Only in prod-lib/([^:]+): (.*)", line)
    if match:
        print "%s/%s\tP" % (match.group(1), match.group(2))
        continue
    match = re.match("Only in svn-lib/([^:]+): (.*)", line)
    if match:
        print "%s/%s\tS" % (match.group(1), match.group(2))
        continue
    match = re.match("Files prod-lib/(.*) and svn-lib/.* differ", line)
    if match:
        print "%s\tD" % match.group(1)
        continue

