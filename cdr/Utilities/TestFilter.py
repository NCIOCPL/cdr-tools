###########################################################
# Test filter a CDR doc from the command line.
#
# Run without args for usage info.
#
# $Id: TestFilter.py,v 1.1 2008-12-19 03:16:09 ameyer Exp $
#
# $Log: not supported by cvs2svn $
###########################################################

import sys, getopt, cdr

# Options
fullOutput = True
opts, args = getopt.getopt(sys.argv[1:], "p")
for opt in opts:
    if opt[0] == '-p':
        fullOutput = False


# usage
if len(args) < 2:
    sys.stderr.write("""
usage: TestFilter.py {opts} doc_id filter {"parm=data..." {"parm=data ..."} ...}

 Options:
   -p = Plain output, just the filtered document, no banners or messages.

 Arguments:
   Filter is one of:
      Filter doc ID number
      "name:this is a filter name"
      "set:this is a filter set name"
   Parms are optional name=value pairs, with quotes if required.
   Do not put spaces around '='.

 Output:
   Results go to stdout:  Output document, then messages if any.
   If plain output (-p), just output the document, no banners or messages.
   Errors to stderr.

 Example:
   TestFilter.py 12345 "name:Small Animal Filter" "animals=dogs cats rabbits"
""")
    sys.exit(1)


# Doc ID is always an integer
docId = int(args[0])

# Filter can be integer or string, test to find out which
filter = args[1]
try:
    filterId = int(filter)
except ValueError:
    # String is passed to filterDoc as a sequence of one string
    filter = [filter,]
else:
    # Number passed as integer
    filter = filterId

# Gather optional parms
parms = []
argx  = 2
while argx < len(args):
    parms.append(args[argx].split('='))
    argx += 1

# Filter doc
session = cdr.login("CdrGuest", "never.0n-$undaY")
resp = cdr.filterDoc(session, filter=filter, docId=docId, parm=parms)

if type(resp) in (type(""), type(u"")):
    sys.stderr.write("Error response:\n  %s" % resp)
    sys.exit(1)

# Output to stdout
if fullOutput:
    print ("""
RESPONSE FROM HOST:
DOCUMENT
----------------------------------
%s
----------------------------------

MESSAGES
----------------------------------
%s
----------------------------------
""" % (resp))

else:
    print (resp[0])
