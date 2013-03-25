#----------------------------------------------------------------------
#
# $Id$
#
# Count the number of files in the CTGovExport directory that have
# Arms information (identified by the existence of the arms_grou_label).
#
# BZIssue::4983 - Arms Count Report Problem
#
# Revision 1.5  2008/10/06 20:07:53  venglisc
# Changed output formatting. (Bug 4123)
#
# Revision 1.4  2008/09/26 14:38:04  venglisc
# Added new option to specify directory, added new function to get a count
# of FDA required elements.
#
# Revision 1.3  2008/06/09 21:26:22  venglisc
# Per request from LG I've added a section to only display trials that are
# new on the report since the last report ran.
#
# Revision 1.2  2008/06/04 18:15:12  venglisc
# Included the CDR-IDs of the arm trials; sending message to recipients
# who are member of a group DL.
#
# Revision 1.1  2008/06/02 14:55:49  venglisc
# Initial copy of script to count the number of protocols submitted to the
# NLM that have Arms information. The number is submitted to LG.
#
#----------------------------------------------------------------------
import subprocess, os, sys, cdr, time, glob, getopt, socket

OUTPUTBASE         = cdr.BASEDIR + "/Output/NLMExport"
UTIL               = os.path.join("d:\\cdr", "Utilities")
TMP                = os.path.join("d:\\cdr", "tmp")
FILEBASE           = "ArmsCount"
LOGFILE            = "%s.log" % FILEBASE
jobTime            = time.localtime(time.time())
dateStamp          = time.strftime("%Y%m%d%H%M%S", jobTime)
elements           = {"is_fda_regulated":[],
                      "is_section_801":[],
                      "delayed_posting":[]}

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
# Find the last file and compare the content to find newly 
# added trials
# ------------------------------------------------------------
def getNewTrials(allTrials = []):
    newTrials = []
    os.chdir(TMP)
    oldFile = glob.glob('ArmsCount*.txt')

    oldFile.sort()
    filename = oldFile[-2:-1][0]
    l.write("Comparing to: %s" % filename, stdout = True)

    f3 = open("%s" % filename)
    oldTrials = f3.readlines()
    f3.close()

    for trial in allTrials:
        for oldTrial in oldTrials:
            if trial == oldTrial:
                break
        else:
            newTrials.append(trial)

    return (newTrials, filename)


# ------------------------------------------------------------
# There are a few yes/no elements that the users would like to
# receive a count for.
# ------------------------------------------------------------
def checkElements():

    # Count the total of all elements
    # -------------------------------
    for element in elements.keys():
        p1 = subprocess.Popen(["grep", "-l", element, "CDR*"],
                              stdout = subprocess.PIPE)
        p2 = subprocess.Popen(["wc", "-l"], 
                              stdin  = p1.stdout,
                              stdout = subprocess.PIPE)
        p3 = subprocess.Popen(["gawk", "{print $1}"],
                              stdin  = p2.stdout,
                              stdout = subprocess.PIPE)
        elements[element].append(p3.communicate()[0])

    # Count the number of documents with 'yes' in the element name
    # ------------------------------------------------------------
    for element in elements.keys():
        p1 = subprocess.Popen(["grep", "-l", element + ">yes", "CDR*"],
                              stdout = subprocess.PIPE)
        p2 = subprocess.Popen(["wc", "-l"], 
                              stdin  = p1.stdout,
                              stdout = subprocess.PIPE)
        p3 = subprocess.Popen(["gawk", "{print $1}"],
                              stdin  = p2.stdout,
                              stdout = subprocess.PIPE)
        elements[element].append(p3.communicate()[0])

    return elements


# ------------------------------------------------------------
# *** Main ***
# Jetzt wird es ernst
# ------------------------------------------------------------

# Open Log file and enter start message
# -------------------------------------
l = cdr.Log(LOGFILE)
l.write('ArmsCount - Started', stdout = True)
l.write('Arguments: %s' % sys.argv, stdout=True)

parseArgs(sys.argv)

# Finding the latest directory created for the NLMExport
# ------------------------------------------------------
os.chdir(OUTPUTBASE)
if not pubDir:
    # We're comparing to last weeks output, so we need to set the 
    # year appropriately during the first week of a year.
    # Note:  The above comment is wrong.
    #        We need to find the latest (Friday/Saturday) export
    #        directory.  This should, by default, be the one just
    #        created.
    # -----------------------------------------------------------
    # now  = time.time()
    # last = now - (6 * 24 * 60 * 60)
    # lastWeeksYear = time.strftime("%Y", time.localtime(last))
    # lastDirs = glob.glob(lastWeeksYear + '*')

    # If we're still running this program after 2099-12-31 the 
    # the text string for glob should be changed.
    # --------------------------------------------------------
    lastDirs = glob.glob('20*')
    lastDirs.sort()
    lastDir = lastDirs[-1:][0]
else:
    lastDir = pubDir

# Finding the studies with ArmsGroups info and write to file
# ----------------------------------------------------------
if testMode:
    filename = '%s%s_test.txt' % (FILEBASE, dateStamp)
else:
    filename = '%s%s.txt' % (FILEBASE, dateStamp)

f1 = open("%s\\%s" % (TMP, filename), 'w')
os.chdir(lastDir)
rcode = subprocess.call(["grep", "-l", "arm_group_label", "CDR*"], 
                        stdout = f1)
f1.close()


# Create the report to count the FDA required elements
# -----------------------------------------------------
l.write('Counting protocols with FDA elements', stdout = True)
countFiles = checkElements()
l.write('Result:\n%s' % str(countFiles),       stdout = True)

fdaStatReport = """\
Element           Total   yes    no
----------------- ----- ----- -----
"""

for element in elements.keys():
    fdaStatReport += "%16s: %5d %5d %5d\n" % (element, 
                                              int(elements[element][0]), 
                                              int(elements[element][1]),
                                              int(elements[element][0]) -
                                                int(elements[element][1]))


# Read the file created and count the number of records
# -----------------------------------------------------
f2 = open("%s\\%s" % (TMP, filename))
armLines = f2.readlines()
f2.close()

# Find the documents that are new since the last publishing
# ---------------------------------------------------------
newTrials, file = getNewTrials(armLines)

# Print the result
# ----------------
l.write('Result for directory:')
l.write('  %s/%s' % (OUTPUTBASE, lastDir))
l.write('  %d studies with Arm/Group information' % len(armLines))
l.write('  %s/%s' % (TMP, file))
l.write('  %d new studies with Arm/Group information' % len(newTrials))

# Setting up email message to be send to users
# --------------------------------------------
machine  = socket.gethostname().split('.')[0]
server   = '%s.nci.nih.gov' % machine
sender   = '***REMOVED***'
if cdr.h.org == 'OCE':
    subject   = "%s: %s" % (cdr.PUB_NAME.capitalize(),
                'List of NLM Studies with ArmsOrGroups')
else:
    subject   = "%s-%s: %s" %(cdr.h.org, cdr.h.tier,
                 'List of NLM Studies with ArmsOrGroups')

body     = """\nResult for Directory:
  %s/%s

  %d studies with Arm/Group information
  %d new studies with Arm/Group information
  (Comparing to file %s)
  

Counting documents by field
===========================
%s


List of "new" Arm/Group Studies
===============================
%s


List of all Arm/Group Studies
=============================
%s""" % (OUTPUTBASE, lastDir, len(armLines), len(newTrials), file, 
           fdaStatReport,
           "".join(id for id in newTrials),
           "".join(id for id in armLines))

# Don't send emails to everyone if we're testing 
# ----------------------------------------------
emailDL = cdr.getEmailList('CTGov Export Arms Notification')
emailDL.sort()
if not len(emailDL) or testMode:
    recips = ["***REMOVED***"]
else:
    recips = emailDL

if recips:
    cdr.sendMail(sender, recips, subject, body)

# All done, going home now
# ------------------------
cpu = time.clock()
l.write('CPU time: %6.2f seconds' % cpu, stdout = True)
l.write('ArmsCount - Finished', stdout = True)
sys.exit(0)
