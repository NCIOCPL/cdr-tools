###########################################################
# Test filter a CDR doc from the command line.
#
# Run without args for usage info.
#
# $Id: TestFilter.py,v 1.4 2008-12-22 16:49:41 ameyer Exp $
#
# $Log: not supported by cvs2svn $
# Revision 1.3  2008/12/22 16:23:51  ameyer
# Added indentation option.
#
# Revision 1.2  2008/12/19 03:49:40  ameyer
# Added file options for doc and filter.
#
# Revision 1.1  2008/12/19 03:16:09  ameyer
# Initial version.
#
###########################################################

import sys, getopt, time, cdr

# For nicely indented output
INDENT_FILTER = """<?xml version="1.0"?>
<xsl:transform version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

<xsl:strip-space elements="*"/>
<xsl:output indent="yes"/>
<xsl:template match="/">
 <xsl:copy-of select = "."/>
</xsl:template>

</xsl:transform>
"""

def getFileContent(fname):
    """
    Return the content of a file as a string.

    Pass:
        filename with optional "file:" at front.

    Return:
        Contents of file as a string.
        Exits if error.
    """
    try:
        fp = open(fname, "r")
        text = fp.read()
        fp.close()
    except IOError, info:
        sys.stderr.write(str(info))
        sys.exit(1)
    return text


# Options
fullOutput   = True
indentOutput = False
opts, args = getopt.getopt(sys.argv[1:], "ip")
for opt in opts:
    if opt[0] == '-i':
        indentOutput = True
    if opt[0] == '-p':
        fullOutput = False

# usage
if len(args) < 2:
    sys.stderr.write("""
usage: TestFilter.py {opts} Doc Filter {"parm=data..." {"parm=data ..."} ...}

 Options:
   -i = Indent output document (pretty print).
   -p = Plain output, just the filtered document, no banners or messages.

 Arguments:
   Doc is one of:
      Doc ID number, no CDR000... prefix.
      OS file name (if there is one non-digit char).
   Filter is one of:
      Filter doc ID number
      "name:this is a filter name"
      "set:this is a filter set name"
      "file:OS filter file name"
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


# Doc ID is an integer or a file name
try:
    docId = int(args[0])
except ValueError:
    docId = None
    doc = getFileContent(args[0])
else:
    doc = None

# Filter can be integer or string, test to find out which
inline = False
filter = args[1]
try:
    filterId = int(filter)
except ValueError:
    # Filter specified as a string.
    # It may be a filename or a "name:" or "set:" CDR identifier
    if filter.startswith("file:"):
        filter = getFileContent(filter[5:])
        inline = True
    elif filter.startswith("name:") or filter.startswith("set:"):
        # String is passed to filterDoc as a sequence of one string
        filter = [filter,]
    else:
        sys.stderr.write('Filter identifier "%s" not recognized' % filter)
        sys.exit(1)
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
startClock = time.clock()
resp = cdr.filterDoc(session, filter=filter, docId=docId, doc=doc,
                     inline=inline, parm=parms)
stopClock = time.clock()

if type(resp) in (type(""), type(u"")):
    sys.stderr.write("Error response:\n  %s" % resp)
    sys.exit(1)

(xml, msgs) = resp

# If pretty printing with indentation
if indentOutput:
    resp = cdr.filterDoc(session, filter=INDENT_FILTER, doc=xml, inline=True)
if type(resp) in (type(""), type(u"")):
    sys.stderr.write("Unable to indent output:\n  %s\n--- continuing:\n" % resp)
else:
    xml = resp[0]

# Output to stdout
if fullOutput:
    print ("""
RESPONSE FROM HOST:  cdr.filterDoc time = %f seconds
DOCUMENT
----------------------------------
%s
----------------------------------

MESSAGES
----------------------------------
%s
----------------------------------
""" % (stopClock - startClock, xml, msgs))

else:
    print (resp[0])
