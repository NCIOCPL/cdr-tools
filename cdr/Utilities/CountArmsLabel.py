#----------------------------------------------------------------------
#
# $Id: CountArmsLabel.py,v 1.3 2008-06-09 21:26:22 venglisc Exp $
#
# Count the number of files in the CTGovExport directory that have
# Arms information (identified by the existence of the arms_grou_label).
#
# $Log: not supported by cvs2svn $
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
FILEBASE           = "ArmsCount"
LOGFILE            = "%s.log" % FILEBASE
jobTime            = time.localtime(time.time())
dateStamp          = time.strftime("%Y%m%d%H%M%S", jobTime)

testMode   = None
fullUpdate = None


# ------------------------------------------------------------
# Function to parse the command line arguments
# Note:  testmode/livemode is currently only used to be passed
#        to the called program
# ------------------------------------------------------------
def parseArgs(args):

    global testMode
    global fullUpdate
    global refresh
    global l

    try:
        longopts = ["testmode", "livemode"]
        opts, args = getopt.getopt(args[1:], "tl", longopts)
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

""" % sys.argv[0].split('\\')[-1])
    sys.exit(1)


# ------------------------------------------------------------
# Find the last file and compare the content to find newly 
# added trials
# ------------------------------------------------------------
def getNewTrials(allTrials = []):
    newTrials = []
    os.chdir('d:\\cdr\\tmp')
    oldFile = glob.glob('ArmsCount*.txt')

    oldFile.sort()
    filename = oldFile[-2:-1][0]
    l.write("Comparing to: ", filename, stdout = True)

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
lastDirs = glob.glob('2008*')
lastDirs.sort()
lastDir = lastDirs[-1:][0]

# Finding the studies with ArmsGroups info and write to file
# ----------------------------------------------------------
if testMode:
    filename = '%s%s_test.txt' % (FILEBASE, dateStamp)
else:
    filename = '%s%s.txt' % (FILEBASE, dateStamp)

f1 = open("d:\\cdr\\tmp\\%s" % filename, 'w')
os.chdir(lastDir)
rcode = subprocess.call(["grep", "-l", "arm_group_label", "CDR*"], 
                        stdout = f1)
f1.close()

# Read the file created and count the number of records
# -----------------------------------------------------
f2 = open("d:\\cdr\\tmp\\%s" % filename)
armLines = f2.readlines()
f2.close()

# Find the documents that are new since the last publishing
# ---------------------------------------------------------
newTrials, file = getNewTrials(armLines)

# Print the result
# ----------------
l.write('Result for directory:',           stdout = True)
l.write('  %s/%s' % (OUTPUTBASE, lastDir), stdout = True)
l.write('  %d studies with Arm/Group information' % len(armLines), 
                                           stdout = True)
l.write('  %s/%s' % (OUTPUTBASE, file), stdout = True)
l.write('  %d new studies with Arm/Group information' % len(newTrials), 
                                           stdout = True)

# Setting up email message to be send to users
# --------------------------------------------
machine  = socket.gethostname().split('.')[0]
server   = '%s.nci.nih.gov' % machine
sender   = '***REMOVED***'
subject  = '%s: List of NLM Studies with ArmsOrGroups' % machine.upper()
body     = """\nResult for Directory:
  %s/%s
  %d studies with Arm/Group information
  %d new studies with Arm/Group information
  (Comparing to file %s)
  
List of "new" Studies
=====================
%s


List of all Studies
===================
%s""" % (OUTPUTBASE, lastDir, len(armLines), len(newTrials), file, 
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
