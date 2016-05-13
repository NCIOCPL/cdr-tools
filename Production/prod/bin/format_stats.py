#!/usr/bin/python
# ******************************************************************
# File Name: format_stats.py
#            ---------------
# Script that takes the changes file from the FTP server and creates
# a formatted TXT file.  This is used when a wrong changes file went
# out and we have to recreate the formatted output from an older
# file
# Intermediate files are stored in the $PDQLOG directory.
# ------------------------------------------------------------------
# $Author$      
# Created:              Volker Englisch  - 2006-03-20
# $Locker:  $
# 
# $Source: /usr/local/cvsroot/production/prod/bin/get_stats.py,v $
# $Revision$
#
# History:
# $Log: $
#
# ******************************************************************
import sys, os, ftplib, time, glob, datetime

!!! Not converted for CBIIT yet !!!

# Setting the variables
# ---------------------
tmpDir  = '/tmp'
pdqLog  = '/pdq/prod/log'
ftpFile = '%s/getchanges.ftp' % tmpDir
pubDir  = '/u/ftp/cdr/pub/pdq/full'

now     = time.time()
lastWk  = time.time() - 5 * 24 * 60 * 60
relDate = time.strftime("%Y%W", time.localtime(lastWk))
relDateHdr = time.strftime("Week %W, %Y", time.localtime(lastWk))
rchanges= '%s.changes'     % relDate
lchanges= '%s_changes.txt' % relDate

# This is the correct way of getting the ISO week number
# The job is scheduled to run on a Sunday (the last day
# of the ISO week) and the same week as the publishing
# job.
# ------------------------------------------------------
today = datetime.date.today()
one_day = datetime.timedelta(1)
one_week = datetime.timedelta(7)
last_week = today - one_week
year, week, weekday = last_week.isocalendar()
WEEK = "%04d%02d" % (year, week)


# Which week are we processing?
# -----------------------------
files = glob.glob('*.changes')
tmpFile = files[0]
thisWeek = tmpFile[4:6]
relDate = relDate[:4] + thisWeek
relDateHdr = relDateHdr[:5] + thisWeek + relDateHdr[7:]

class CommandResult:                                                            
    def __init__(self, code, output):                                           
        self.code   = code                                                      
        self.output = output                                                    

def runCommand(command):                                                        
    commandStream = os.popen('%s 2>&1' % command)                               
    output = commandStream.read()                                               
    code = commandStream.close()                                                
    return CommandResult(code, output)         

# Creating the ftp files to perform the download
# ----------------------------------------------
print 'Getting the statistics files...ve'

try:
    ftpDir = '/u/ftp/pub/pdq/full'
    ftpFile = '%s' % (rchanges)
    ftpFile = tmpFile
    ### ftp = ftplib.FTP(FTPSERVER)
    ### ftp.login(FTPUSER, FTPPWD)
    ### chCwd = ftp.cwd(pubDir)
    ### print ftp.pwd()
    ### # ftp.dir()
    ### print "%s" % chCwd
    os.chdir(pdqLog)
    print "FtpFile: %s" % ftpFile

    ### file = open(ftpFile, 'w')
    ### a = ftp.retrbinary('RETR %s' % ftpFile, file.write) # , file.write())
    ### print a
    ### file.close()
    ### print "Bytes transfered %d" % ftp.size(ftpFile)
except ftplib.Error, msg:
    print '*** FTP Error ***\n%s' % msg
    sys.exit(1)

# Reading the data in
# -------------------
### file = open(pdqLog + '/' + rchanges, 'r')
### file = open('tmp/' + rchanges, 'r')
file = open('/tmp/' + tmpFile, 'r')
records = file.read()
file.close()

# Manipulating the data to create a formatted output file
# -------------------------------------------------------
lines = records.split()

stat = {}
change = {}
i = 0
for line in lines:
    i += 1
    mysplit = line.split(':')
    change[mysplit[1]] = mysplit[2]
    stat[mysplit[0]] = change
    if i % 3 == 0:
       change = {}


# Write the data to the log directory
# -----------------------------------
print 'Writing formatted changes file...'
### sf = open(pdqLog + '/' + lchanges, 'w')
sf = open('/tmp/' + tmpFile + '.txt', 'w')
sf.write('\n\nChanged Documents for %s\n' % relDateHdr)
sf.write('===================================\n\n')
sf.write('Document Type            added  modified  removed\n')
sf.write('---------------------  -------  --------  -------\n')

docType = stat.keys()
docType.sort()

for docs in docType:
   sf.write('%20s:  %7s  %8s  %7s\n' % (docs.replace('.' + relDate, ''), 
                                 stat[docs]['added'], 
                                 stat[docs]['modified'], 
                                 stat[docs]['removed']))
sf.write('\n')
sf.close()
print 'Done.'
