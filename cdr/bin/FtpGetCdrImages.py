#----------------------------------------------------------------------
#
# File Name: FtpGetCdrImages.py
# =============================
# Script to copy files from the CIPSFTP server to the CIPS Network.
# It is intended to copy image files from a subdirectory of the CIPSFTP
# directory
#    /u/ftp/qa/ciat/Images
# and copy all files from that directory to the network on the public
# drive
#    k:\CDR Images\Images_from_CIPSFTP
#
# $Id: FtpGetCdrImages.py,v 1.1 2004-10-14 21:18:51 venglisc Exp $
# $Log: not supported by cvs2svn $
#
#----------------------------------------------------------------------
import sys, re, string, cdr, os, shutil, time

if len(sys.argv) < 2:
   sys.stder.write('usage: FtpGetCdrImages.py directory-name \n')
   sys.exit(1)

# Setting directory and file names
# --------------------------------
log = "d:\\cdr\\log\\FtpGetCdrImages.log" 
netwkDir = 'k:\\' + os.path.join('CDR Images', 'Images_from_CIPSFTP')
imageDir = '/u/ftp/qa/ciat/Images/' + sys.argv[1]
dateStr = time.strftime("%Y-%m-%d-%H%M", time.localtime())
divider = "=" * 65

print "Copy files from CIPSFTP:", imageDir
print "to network directory   :", netwkDir


# Open Log file and enter start message
# -------------------------------------
open(log, "a").write("%s\nFtp: Started at %s\n" % \
                    (divider, time.ctime(time.time())))
try:

    # Creating the FTP command file
    # -----------------------------
    open(log, "a").write("   : Creating ftp command file\n")
    os.chdir(netwkDir)
    ftpCmd = open ('FtpGetCdrImages.txt', 'w')
    ftpCmd.write('open cipsftp.nci.nih.gov\n')
    ftpCmd.write('cdrdev\n')
    ftpCmd.write('***REMOVED***\n')
    ftpCmd.write('binary\n')
    ftpCmd.write('cd ' + imageDir + '\n')
    ftpCmd.write('bin\n')
    ftpCmd.write('mget *\n')
    ftpCmd.write('bye\n')
    ftpCmd.close()

    open(log, "a").write("   : Copy image files from ftp server\n")

    # FTP the Hot-fix documents to ftpserver
    # --------------------------------------
    mycmd = cdr.runCommand("c:/Winnt/System32/ftp.exe -i -s:FtpGetCdrImages.txt")

    open(log, "a").write("   : FTP command return code: %s\n" %
                        (mycmd.code))
    if mycmd.code == 1:
       open(log, "a").write("   : ---------------------------\n%s\n" %
                        (mycmd.output))

    open(log, "a").write("   : Ended   at: %s\n%s\n" %
                        (time.ctime(time.time()), divider))

except StandardError, arg:
    open(log, "a").write("   : Failure: %s\n%s\n" % 
                        (arg[0], divider))

except SystemExit:
    # The mailers invoke sys.exit(0) when they're done, raising this exception.
    pass

except:
    open(log, "a").write("   : Unexpected failure\n%s\n" % 
                        (divider))
