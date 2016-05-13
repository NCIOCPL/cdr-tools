#----------------------------------------------------------------------
# Strip out noise from a deploy-all.py diff file.
#----------------------------------------------------------------------
import sys
import re

SKIP = ("CdrClientDebug", "CDRLoader.cmd", "CdrRunAgain.cmd", "CdrManifest.xml")
BIN = ("CdrServer.exe", "CdrService.exe", "ShutdownCdr.exe", "Cdr.dll")
PATTERNS = (r"CdrServer-\d{8}.exe", r"CdrClient-\d{14}.exe",
            r"CdrServer.exe-\d{8}", r"^Only in .*\.pyc$", r"^Only in .*~$")
def do_block(block, strip_tail=False):
    sys.stdout.write("diff -br ")
    lines = block.splitlines()
    if strip_tail:
        lines = lines[:-5]
    for skip in SKIP:
        if skip in lines[0]:
            return
    for line in lines:
        if not skip_binary_diff(line):
            print line
def skip_binary_diff(line):
    for bin in BIN:
        if "%s differ" % bin in line:
            return True
    for pattern in PATTERNS:
        if re.search(pattern, line):
            return True
    return False
#lines = sys.stdin.readlines()[4:-5]
diff = sys.stdin.read()
blocks = diff.split("diff -br ")
for line in blocks[0].splitlines()[4:]:
    if not skip_binary_diff(line):
        print line
for block in blocks[1:-1]:
    do_block(block)
do_block(blocks[-1], True)
#print len(blocks), "blocks"
