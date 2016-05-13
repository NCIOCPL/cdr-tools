#!/usr/bin/python
# ********************************************************************
# File name: ask-for-data.py
#            ---------------
# Test harness to access PDQ content partner information from the CDR
# ********************************************************************

import urllib2
import getopt
import cdrutil
import sys

# Setting the variables
# ---------------------
tmpDir  = '/tmp'
BINDIR  = '/home/cdroperator/prod/bin'
LOGDIR  = '/usr/local/cdr/log'
LOGFILE = '%s/ask-for-data.log' % LOGDIR

testMode = None
product = None
logFile = None

# ---------------------------------------------------------------
# Function to parse the command line arguments
# Options will be implemented if needed in the future
# ---------------------------------------------------------------
def parseArgs(argv):
    args = argv

    global testMode
    global product
    global logFile

    try:
        longopts = ["testmode", "livemode", "product=", "logfile="]
        opts, args = getopt.getopt(args[1:], "tlp:o:", longopts)
    except getopt.GetoptError, e:
        usage(argv)

    for o, a in opts:
        if o in ("-t", "--testmode"):
            testMode = True
            cdrutil.log("running in TEST mode", logfile=LOGFILE)
        elif o in ("-l", "--livemode"):
            testMode = False
            cdrutil.log("running in LIVE mode", logfile=LOGFILE)
        elif o in ("-p", "--product"):
            product = False
            cdrutil.log("running for product: %s" % product, logfile=LOGFILE)
        elif o in ("-o", "--logfile"):
            logFile = a
            cdrutil.log("setting logfile to %s" % logFile, logfile=LOGFILE)

    if args:
       usage(argv)
    if testMode is None:
       usage(argv)

    return()


# ------------------------------------------------------------------
# Module to display the default usage
# ------------------------------------------------------------------
def usage(args):
    print args
    sys.stderr.write("""\
usage: %s [options]

options:
    -l, --livemode
           run in LIVE mode

    -t, --testmode
           run in TEST mode

    -p, --product
           run for specified product

    -o, --logfile
           Log file name (default: PDQAcessReport.log)
""" % args[0].split('/')[-1])
    sys.exit(1)


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
parseArgs(sys.argv)

if testMode:
    product = 'TEST'
else:
    product = 'CDR'

f = urllib2.urlopen(
          "https://cdr-dev.cancer.gov/cgi-bin/cdr/get-pdq-contacts.py?p=%s" % 
                                                                  product)
print f.read()
