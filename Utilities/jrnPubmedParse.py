############################################################
# $Id$
#
# Parse a Pubmed journal list and output a text list suitable for
# comparisons to PsychINFO.
#
# Author: AHM
#   Date: June 2010
#
# BZIssue::4858
#############################################################
import sys

if len(sys.argv) != 2:
    sys.stderr.write("""
usage: jrnPubmedParse.py inputfilename

    See jrnPsychParse.py for more info.  Output is the same.
""")
    sys.exit(1)

fp = open(sys.argv[1])

THDR = "JournalTitle: "
IHDR = "ISSN: "
EHDR = "ESSN: "
NLMID = "NlmId: "

TLEN = len(THDR)
ILEN = len(IHDR)
ELEN = len(EHDR)

while True:
    line = fp.readline()
    if line[-1:] == "\n":
        line = line[:-1]
    if not line:
        break

    if line.startswith(THDR):
        # Got a new title, blank out issns
        title = line[TLEN:]
        issn  = "         "
        eissn = "         "

    if line.startswith(IHDR):
        tmp = line[ILEN:]
        if tmp:
            issn = tmp

    if line.startswith(EHDR):
        tmp = line[ELEN:]
        if tmp:
            eissn = tmp

    if line.startswith(NLMID):
        # We've got everything we want, write it out
        print("%s\t%s\t%s" % (issn, eissn, title))
