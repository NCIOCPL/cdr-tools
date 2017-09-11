import cdr
import sys

if len(sys.argv) not in (2, 3):
    print "usage: turn-on-ctrp-force-reimport.py CDR-SESSION-ID \"COMMENT\""
    sys.exit(1)
if len(sys.argv) == 2:
    cdr.updateCtl(sys.argv[1], "Create", "ctrp", "force-reimport", "true")
if len(sys.argv) == 3:
    cdr.updateCtl(sys.argv[1], "Create", "ctrp", "force-reimport", "true",
                  comment=sys.argv[2])
print "force-reimport turned on"
