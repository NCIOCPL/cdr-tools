#----------------------------------------------------------------------
#
# $Id: $
#
# OCCM requested a report listing all GlossaryTerms related to some
# given words.  All words are somewhat related to smoking.
# The program expects all vendor GlossaryTerm documents to be available
# in a single directory (OUTPUTBASE).  Each file is opened, parsed, 
# and the TermDefinition is searched for one of the given words.
# The output is written as a CSV file.
#
# BZIssue::5267 - Report of tobacco-related glossary terms
#
#----------------------------------------------------------------------
import subprocess, os, sys, cdr, time, glob, getopt, socket, re
from lxml import etree

OUTPUTBASE         = "D:\\home\\venglisch\\temp\\Glossary"
UTIL               = os.path.join("d:\\cdr", "Utilities")
TMP                = os.path.join("d:\\cdr", "tmp")
FILEBASE           = "GlossaryTobacco"
LOGFILE            = "%s.log" % FILEBASE
jobTime            = time.localtime(time.time())
dateStamp          = time.strftime("%Y%m%d%H%M%S", jobTime)
searchStrings      = { u"tobacco",
                       u"smoke",
                       u"smoker",
                       u"smoking",
                       u"chemical",
                       u"nicotine",
                       u"tar",
                       u"inhale",
                       u"betel ",
                       u"chewing",
                       u"cigar",
                       u"cigarette",
                       u"cessation",
                       u"pipe",
                       u"respiratory"}

testMode   = None
fullUpdate = None
pubDir     = None


# ------------------------------------------------------------
# Function to parse the command line arguments
# Note:  testmode/livemode is currently only used to be passed
#        to the called program
# ------------------------------------------------------------
def parseArgs(args):

    global testMode
    global fullUpdate
    global pubDir
    global l

    try:
        longopts = ["logfile=", "directory=", "testmode", "livemode"]
        opts, args = getopt.getopt(args[1:], "o:d:tl", longopts)
    except getopt.GetoptError, e:
        usage(args)

    for o, a in opts:
        if o in ("-o", "--logfile"):
            global LOGFILE
            LOGFILE = a
            l = cdr.Log(LOGFILE)
        elif o in ("-t", "--testmode"):
            testMode = True
            l.write("running in TEST mode")
        elif o in ("-l", "--livemode"):
            testMode = False
            l.write("running in LIVE mode")
        elif o in ("-d", "--directory"):
            pubDir = a
            l.write("using directory %s" % pubDir)

    if len(args) > 0:
        usage(args)
    if testMode is None:
        usage(args)

    return


# ------------------------------------------------------------
# Function to display the default usage
# ------------------------------------------------------------
def usage(args):
    print args
    sys.stderr.write("""\
usage: %s [--livemode|--testmode] [options]

options:
    -t, --testmode
           run in TEST mode

    -l, --livemode
           run in LIVE mode

    -d, --directory
           specify latest weekly publishing directory name

""" % sys.argv[0].split('\\')[-1])
    sys.exit(1)


# ------------------------------------------------------------
# *** Main ***
# Jetzt wird es ernst
# ------------------------------------------------------------

# Open Log file and enter start message
# -------------------------------------
l = cdr.Log(LOGFILE)
l.write('GetGlossaryDef - Started', stdout = True)
l.write('Arguments: %s' % sys.argv, stdout=True)

parseArgs(sys.argv)

# Change to the directory with the vendor output files
# ------------------------------------------------------
os.chdir(OUTPUTBASE)

# Open the output file
# ----------------------------------------------------------
if testMode:
    filename = '%s%s_test.csv' % (FILEBASE, dateStamp)
else:
    filename = '%s%s.csv' % (FILEBASE, dateStamp)

# Selecting all files stored in the vendor data directory
# -------------------------------------------------------
allFiles = glob.glob('*.xml')

# Open the output file and create the heading row
# -----------------------------------------------
l.write('Open output file %s' % filename, stdout = True)
f1 = open("%s\\%s" % (TMP, filename), 'w')
f1.write(u'"CDR-ID","Matched Word","Term Name","Definition"\n')

# Loop through the list of vendor output files.
# ---------------------------------------------
l.write('Searching for words in list', stdout = True)
for filename in allFiles:
    # Parsing the file and finding the elements to be displayed
    # ---------------------------------------------------------
    tree = etree.parse(filename)
    gId   = tree.find('[@id]').attrib['id']
    gName = tree.find('TermName')
    gnText= gName.text
    gDef  = tree.find('TermDefinition')
    gdText = gDef.find('DefinitionText').text

    # Loop through the list of words to hit and write record to file
    # Exit the loop if record has been found once (don't need dups)
    # --------------------------------------------------------------
    for word in searchStrings:
        try:
            if re.search(r'\b%s\b' % word, gdText.lower()):
                f1.write('%s,"%s","%s","%s"\n' % (int(gId[3:]), 
                                                word.encode('utf-8'), 
                                                gnText.encode('utf-8'), 
                                                gdText.encode('utf-8')))
                break
        except TypeError, info:
            print '%s: Type Error for word "%s" in Definition' % (int(gId[3:]),
                                                                  word)
            break
        except AttributeError, info:
            print '%s: Error for word "%s" in Definition' % (int(gId[3:]),
                                                                  word)
            break
    
f1.close()
    
# All done, going home now
# ------------------------
cpu = time.clock()
l.write('CPU time: %6.2f seconds' % cpu, stdout = True)
l.write('GetGlossaryDef - Finished', stdout = True)
sys.exit(0)
