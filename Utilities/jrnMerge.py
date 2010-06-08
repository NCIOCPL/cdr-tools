############################################################
# $Id$
#
# Campare the output of jrnPsychParse.py and jrnPubmedParse.py
#
# Produce difference info to stdout.
#
# Author: AHM
#   Date: June 2010
#
# BZIssue::4858
#############################################################
import sys, codecs

if len(sys.argv) != 3:
    sys.stderr.write("""
usage: jrnMerge.py inputPsychInfoFile inputPubmedFile

    See jrnPsychParse.py for description of the inputs
""")
    sys.exit(1)

class Journal:
    """
    Data for one journal.
    """
    def __init__(self, issn, eissn, title):
        self.title     = u"" + title
        self.issn      = issn
        self.eissn     = eissn
        self.processed = False

    def __repr__(self):
        """
        Format for output.
        """
        tmp = self.title.replace(u"\n", u"")
        tmp = u"%s\t%s\t%s" % (self.issn, self.eissn, tmp)
        utf = tmp.encode("utf-8")
        return utf

# number -> Journal object ref lookup
issnLookup  = {}
eissnLookup = {}

# Open output files
outCommon = open("jrnCommonTitles.txt", "w")
outPubmed = open("jrnPubmedOnlyTitles.txt", "w")
outPsych  = open("jrnPsychInfoOnlyTitles.txt", "w")
outUnknown= open("jrnUnnumberedTitles.txt", "w")

# Load PscyhINFO journals
fp = codecs.open(sys.argv[1], encoding='utf-8')
while True:
    line = fp.readline()
    if line[-1:] == "\n":
        line = line[:-1]
    if not line:
        break

    issn, eissn, title = line.split('\t')
    jrnl = Journal(issn, eissn, title)

    # If no issn or eissn, we can't match these titles
    if issn == "         " and eissn == "         ":
        outUnknown.write("%s\n" % jrnl)
    else:
        # Store mappings
        issnLookup[issn]   = jrnl
        eissnLookup[eissn] = jrnl
fp.close()

# Lookup all the pubmed journals
fp = open(sys.argv[2])
while True:
    line = fp.readline()
    if line[-1:] in ("\r", "\n"):
        line = line[:-1]
    if not line:
        break

    issn, eissn, title = line.split('\t')

    # Handle cases of journals with no issn or eissn
    if issn == "         " and eissn == "         ":
        outUnknown.write("%s\t%s\t%s\n" % (issn, eissn, title))
        continue

    # Lookup and output
    if issn != "         " and issnLookup.has_key(issn):
        # Output the Pubmed version, it's plain ASCII
        outCommon.write("%s\t%s\t%s\n" % (issn, eissn, title))
        issnLookup[issn].processed = True
    elif eissn != "         " and eissnLookup.has_key(eissn):
        outCommon.write("%s\t%s\t%s\n" % (issn, eissn, title))
        eissnLookup[eissn].processed = True

    else:
        # Found in Pubmed but not in PsychINFO
        outPubmed.write("%s\t%s\t%s\n" % (issn, eissn, title))
fp.close()
outCommon.close()
outPubmed.close()

# Anything left over is in PsychINFO but not Pubmed
psychJrnlKeys = issnLookup.keys()
for issn in psychJrnlKeys:
    if not issnLookup[issn].processed:
        outPsych.write("%s\n" % issnLookup[issn])

outPsych.close()
outUnknown.close()
