#----------------------------------------------------------------------
#
# $Id: Request1867.py,v 1.2 2005-10-18 15:34:15 ameyer Exp $
#
# One off program to report on differences between current working
# versions of CTGovProtocol documents and their last publishable
# versions.  Done for Bugzilla Request 1867.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2005/10/13 14:31:14  ameyer
# Report on CTGovImport CWD/PubVer differences.
#
#
#----------------------------------------------------------------------

import sys, os, time, textwrap, cdr, cdrdb, cdrcgi

# Define an output report in the temp directory
if os.environ.has_key("TEMP"):
    workdir = os.environ["TEMP"]
else:
    workdir = ""
RPTFILE = workdir + "/CurrentCTGovProtocolDiffsReport.html"
rptf    = None


#----------------------------------------------------------------------
# Append information to the report file
#----------------------------------------------------------------------
def report(msg):
    """
    Output text to the report file.

    Pass:
        Text to output.
    """
    global RPTFILE, rptf

    if not rptf:
        rptf = open(RPTFILE, "w")

    rptf.write(msg)
    rptf.write("\n")

#--------------------------------------------------------------------
# Wrap long lines in the report.
#--------------------------------------------------------------------
def wrap(report):
    """
    Copied from DiffCTGovProtocol.py, see note in next function.
    """
    report = report.replace("\r", "")
    oldLines = report.split("\n")
    newLines = []
    for line in oldLines:
        # Wrap, terminate, and begin each line with a space
        newLines.append(" " + "\n ".join(textwrap.wrap(line, 90)))

    # Return them into a unified string
    return ("\n".join(newLines))

#----------------------------------------------------------------------
# Find doc differences
#----------------------------------------------------------------------
def diffDocs(docIdStr, ver):
    """
    Derive a difference report from an external diff program
    between the current working version of a document and some
    saved version.

    Pass:
        Document id as "CDRnnnnnnnnnn"
        Version number

    Return:
        Difference text
    """
    # Following is lifted from DiffCTGovProtocol.py
    # If turns out not to be a one-off, we might reconsider the copy
    filt     = ['name:Extract Significant CTGovProtocol Elements']
    response = cdr.filterDoc('guest', filt, docIdStr)
    if type(response) in (type(""), type(u"")):
        fatal(response)
    docCWD = unicode(response[0], 'utf-8')

    response = cdr.filterDoc('guest', filt, docIdStr, docVer=ver)
    if type(response) in (type(""), type(u"")):
        fatal(response)
    docVer = unicode(response[0], 'utf-8')

    name1 = "CWD.xml"
    name2 = "LPV.xml"
    doc1  = wrap(docCWD.encode('ascii', 'replace'))
    doc2  = wrap(docVer.encode('ascii', 'replace'))
    cmd   = "diff -aiu %s %s" % (name1, name2)
    try:
        workDir = cdr.makeTempDir('diff')
        os.chdir(workDir)
    except StandardError, args:
        fatal(str(args))
    f1 = open(name1, "w")
    f1.write(doc1)
    f1.close()
    f2 = open(name2, "w")
    f2.write(doc2)
    f2.close()
    result = cdr.runCommand(cmd)
    try:
        os.chdir("..")
        cdr.runCommand("rm -rf %s" % workDir)
    except:
        pass

    # Return pre-formatted, colorized output, or None.
    if not result.output:
        diffText = None
    else:
        diffText = "<pre>\n" + cdrcgi.colorDiffs(result.output) + "\n</pre>\n"
    return diffText



#----------------------------------------------------------------------
# Fatal error
#----------------------------------------------------------------------
def fatal(msg):
    """
    Display error message and abort.

    Pass:
        Message
    """
    report("<h2><font color='red'>%s</font></h2>" % msg)
    sys.stderr.write("Fatal Error: %s" % msg)
    sys.exit(1)


# Connect
try:
    conn   = cdrdb.connect()
    cursor = conn.cursor()
except cdrdb.Error, info:
    fatal("Unable to connect to database:\n%s" % str(info))

# Login
session = cdr.login("CdrGuest", "never.0n-$undaY")
if session.find("<Err") >= 0:
    fatal("Unable to login:\n%s" % session)

report("""
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>Current CTGovProtoco vs. Published Versions Report</title>
 </head>
 <body>
 <h1>Current CTGovProtoco vs. Published Versions Report</h1>

<h2>Date: %s</h2>

<p>The following report lists all CTGovProtocols for which the
current working document was stored with the comment
"ImportCTGovProtocols: creating new CWD"</p

<p>For each document, the report lists the following information:</p>
<dl>
 <dt>Documents that are identical to the last publishable version,
     or for which there are no significant differences:</dt>
 <dd>Prints the CDR document id, with a notation that the current
     working document and last publishable version are equivalent.</dd>
 <dt>Documents for which there are no publishable version:</dt>
 <dd>Prints the CDR document id, with a notation that there are no
     publishable versions of this document.</dd>
 <dt>Documents for which there are significant differences:</dt>
 <dd>Prints the version number of the last publishable version, followed
     by a diff report showing the differences in significant fields.</dd>
</dl>
<hr />
<hr />
""" % time.ctime())

# Find all current working versions that aren't identical to pub versions.
qry = """
SELECT d.id
  FROM document d, doc_type t
 WHERE d.doc_type = t.id
   AND t.name = 'CTGovProtocol'
   AND d.comment = 'ImportCTGovProtocols: creating new CWD'
"""

try:
    cursor.execute(qry)
    docIds = [row[0] for row in cursor.fetchall()]
except cdrdb.Error, info:
    fatal("Unable to select documents to version:\n%s" % str(info))

# Counts
samePubVerCnt = 0
noPubVerCnt   = 0
diffPubVerCnt = 0
noDiffVerCnt  = 0
totalCnt      = 0

# Process each one
for docId in docIds:

    # Full CDRnnnnnnnnnn form of doc id
    docIdStr = cdr.exNormalize(docId)[0]
    totalCnt += 1

    # Get info on last versions
    (lastVer, lastPubVer, isChanged) = cdr.lastVersions(session, docIdStr)

    if (lastPubVer == -1):
        report("<h3>%s has no publishable versions.</h3>" % docIdStr)
        noPubVerCnt += 1
        continue;

    # Do the diff
    diffText = diffDocs(docId, lastPubVer)
    if not diffText:
        report("<h3>%s is equivalent to " % docIdStr \
             + "last publishable version: %d</h3>" % lastPubVer)
        noDiffVerCnt += 1
    else:
        report("<h3>%s differences from last publishable version: %d</h3>" % \
                (docIdStr, lastPubVer))
        report(diffText)
        diffPubVerCnt += 1

# Final report
report("""
<h2>Summary Statistics:</h2>

<table border='1' align='center'>
<tr>
 <th>Documents selected</th><td align='right' width='30'>%d</td>
</tr>
<tr>
 <th>No published version exists</th><td align='right'>%d</td>
</tr>
<tr>
 <th>Docs with differences</th><td align='right'>%d</td>
</tr>
<tr>
 <th>Docs with no significant differences</th><td align='right'>%d</td>
</tr>
</table>
""" % (totalCnt, noPubVerCnt, diffPubVerCnt, noDiffVerCnt))

report("""
</body>
</html>
""")
rptf.close()
