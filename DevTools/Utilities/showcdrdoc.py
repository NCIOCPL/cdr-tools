#!/usr/bin/env python
##############################################################
# Retrieve a CDR document into a formatted web browser display
##############################################################

import sys, os, tempfile, re, time, cdr;

# Defaults
host = 'localhost'
port =  2019
ver  = 'Current'

# Args
if len(sys.argv) < 2 or len(sys.argv) > 5:
    sys.stderr.write("usage: %s doc_id {version, host, port}\n" % sys.argv[0])
    sys.stderr.write("   defaults: version=%s host=%s port=%s\n" % \
                     (ver, host, port))
    sys.exit(1);
try:
    docId = cdr.exNormalize(sys.argv[1])[1]
except cdr.Exception as info:
    sys.stderr.write(str(info))
    sys.exit(1)
if len(sys.argv) > 2:
    ver = sys.argv[2]
if len(sys.argv) > 3:
    host = sys.argv[3]
if len(sys.argv) > 4:
    port = int(sys.argv[4])

# Search returned data for errors or xml document
getErrPat = re.compile(r"^<Errors>.*<Err>(?P<msg>.*)</Err>", re.DOTALL)
getXmlPat = re.compile(r"<!\[CDATA\[(?P<xml>.*)]]>", re.DOTALL)

# Fetch doc from database
cdataDoc = cdr.getDoc('guest', docId, version=ver, host=host, port=port)

# Check for errors
match = getErrPat.search(cdataDoc)
if match:
    msg = match.group('msg')
    sys.stderr.write("%s\n" % msg)
    sys.exit(1)

# Temp data goes here
tmpDir = tempfile.gettempdir()

# Extract xml from CDATA section
match = getXmlPat.search(cdataDoc)
if not match:
    sys.stderr.write("Couldn't find CDATA in doc\n")
    sys.exit(1)
xml = match.group('xml')

# Save xml where browser can get it
fname = "%s/%s" % (tmpDir, "tempDisplayFile.xml")
fobj = open(fname, "w")
fobj.write(xml)
fobj.close()

# Open a browser window on it - assumes browser location
url = 'file://%s' % fname
try:
    cmdStream = os.popen("start %s" % url)
    code = cmdStream.close()
    if code:
        sys.stderr.write (str(code))
except:
    sys.stderr.write("Error starting browser")

