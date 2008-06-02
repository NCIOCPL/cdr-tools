#----------------------------------------------------------------------
#
# $Id: CountArmsLabel.py,v 1.1 2008-06-02 14:55:49 venglisc Exp $
#
# Count the number of files in the CTGovExport directory that have
# Arms information (identified by the existence of the arms_grou_label).
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import subprocess, os, sys, cdr, time, glob, socket

OUTPUTBASE         = cdr.BASEDIR + "/Output/NLMExport"
TARNAME            = "clinical_trials.tar.bz2"
TARCMD             = "d:\\cygwin\\bin\\tar.exe"
FILEBASE           = "ArmsCount"
jobTime            = time.localtime(time.time())
dateStamp          = time.strftime("%Y%m%d%H%M%S", jobTime)


# Finding the latest directory created for the NLMExport
# ------------------------------------------------------
os.chdir(OUTPUTBASE)
lastDirs = glob.glob('2008*')
lastDirs.sort()
lastDir = lastDirs[-1:][0]

# Finding the studies with ArmsGroups info and write to file
# ----------------------------------------------------------
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

# Print the result
# ----------------
print 'Result for directory:'
print '  %s/%s' % (OUTPUTBASE, lastDir)
print '  %d studies with Arm/Group information' % len(armLines)

machine = socket.gethostname().split('.')[0]
server  = '%s.nci.nih.gov' % machine
sender  = '***REMOVED***'
subject = '%s: Count of NLM ArmsOrGroups Trials' % machine.upper()
body    = """\nResult for Directory:
  %s/%s
  %d studies with Arm/Group information""" % (OUTPUTBASE, lastDir, 
                                              len(armLines))
recips = ["***REMOVED***"]
if recips:
    cdr.sendMail(sender, recips, subject, body)
sys.exit()
