#----------------------------------------------------------------------
#
# $Id: Request1867.py,v 1.4 2005-10-25 23:10:54 ameyer Exp $
#
# One off program to report on differences between current working
# versions of CTGovProtocol documents and their last publishable
# versions.  Done for Bugzilla Request 1867.
#
# $Log: not supported by cvs2svn $
# Revision 1.3  2005/10/21 03:40:20  ameyer
# Major rewrite to meet the real requirements.
#
# Revision 1.2  2005/10/18 15:34:15  ameyer
# Using textwrap to word wrap lines for diff.
#
# Revision 1.1  2005/10/13 14:31:14  ameyer
# Report on CTGovImport CWD/PubVer differences.
#
#
#----------------------------------------------------------------------

import sys, os, re, time, cgi, textwrap, cdr, cdrdb, cdrcgi

# Define an output report in the temp directory
if os.environ.has_key("TEMP"):
    workdir = os.environ["TEMP"]
else:
    workdir = ""

# Report output file
RPTFILE = workdir + "/CurrentCTGovProtocolDiffsReport.html"
rptf    = None

# Pattern for PDQIndexing/EntryDate = YYYY-MM-DD
DATEPAT = re.compile(r"\d{4}-\d{2}-\d{2}")

#----------------------------------------------------------------------
# Extract the PDQIndexing/EntryDate from a CTGovImportProtocol
#----------------------------------------------------------------------
def getEntryDate(docId, verNum):
    """
    Extract the date from some version of a CTGovImportProtocol.

    Pass:
        Document ID
        Version number. If None, get CWD.

    Return:
        Date as a string.  Should be in form YYYY-MM-DD.
        None if no EntryDate found or date is malformed (might
            for example be a PI invoking an XMetal macro)
    """
    xsl = """\
<?xml version="1.0"?>
<xsl:transform       xmlns:xsl = "http://www.w3.org/1999/XSL/Transform"
                     xmlns:cdr = "cips.nci.nih.gov/cdr"
                       version = "1.0">
<xsl:output             method = "text"/>
<xsl:template            match = "@*|comment()|*|
                                  processing-instruction()|text()">
 <xsl:apply-templates/>
</xsl:template>
<xsl:template            match = "/CTGovProtocol/PDQIndexing/EntryDate">
 <xsl:value-of          select = "."/>
</xsl:template>
</xsl:transform>
"""
    # Extract date
    result = cdr.filterDoc("guest", xsl, docId=docId, inline=True,
                            docVer=verNum)
    if type(result) == type(""):
        print("ERROR: %s" % result)
        sys.abort(1)
    else:
        strDate = result[0]

    # Test for well-formedness
    if DATEPAT.match(strDate):
        return strDate
    return None

#----------------------------------------------------------------------
# Find the right version to compare CWD to
#----------------------------------------------------------------------
def findCheckVersion(docId, entryDate, lastVer):
    """
    Search the version archive to find the first version
    of a document with an EntryDate matching the passed date.

    I originally planned to do a binary search, but the results
    could be pathological if EntryDate values are out of order.
    Since human beings create these dates, an out of order
    sequence is possible.  So I've reverted to a brute force
    look backwards.  This could get a wrong result if someone
    enters a wrong date, but at least the search will eventually
    end and "garbage in ...".

    If unable to find any matching EntryDate, then it returns None.

    Pass:
        Document ID.
        EntryDate value, as a string, exactly as taken from the CWD.
        Version number of last stored version.

    Return:
        Version number found.
        None if no version matches.
    """
    ver = lastVer
    while ver > 0:
        verDate = getEntryDate(docId, ver)
        if not verDate or verDate < entryDate:
            # We've gone one past the first version with this date
            if ver == lastVer:
                return None
            return ver + 1
        ver -= 1

    # No versions have an older EntryDate, the first version
    #  is our match.
    return 1

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
        line = " " + "\n ".join(textwrap.wrap(line, 90))
        newLines.append(line)

    # Return them in a unified string
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
    doc1  = wrap(docCWD.encode('latin-1', 'replace'))
    doc2  = wrap(docVer.encode('latin-1', 'replace'))
    cmd   = "diff -a -i -w -B -U 1 %s %s" % (name2, name1)
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
        diffText = "<pre>\n" + cdrcgi.colorDiffs(cgi.escape(result.output)) \
                 + "\n</pre>\n"
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
  <title>Current CTGovProtoco vs. Stored Versions Report</title>
 </head>
 <body>
 <h1>Current CTGovProtocols vs. Published Versions Report</h1>

<h2>Date: %s</h2>

<p>The following report lists all CTGovProtocols.  For each protocol,
it searches for the earliest stored version that has the same
PDQIndexing/EntryDate as the current working document.  Both
publishable and non-publishable versions are examined.</p>

<p>For each document, the report lists the following information:</p>
<dl>
 <dt>Documents for which no versions have ever been stored:</dt>
 <dd>Prints the CDR document id, with a notation that there are
     no stored versions of the document.</dd>
 <dt>Documents for which the current working document has no EntryDate</dt>
 <dd>Prints the CDR document id, with a notation that the CWD has
     no PDQIndexing/EntryDate.</dd>
 <dt>Documents for which every stored version has an earlier EntryDate</dt>
 <dd>Prints the CDR document id, with a notation that the CWD must be
     current.</dd>
 <dt>Documents for which there are significant differences:</dt>
 <dd>Prints the version number of the first version with the CWD
     entry date, followed by a diff report showing the differences
     in significant fields.</dd>
 <dt>Documents for which there are NO significant differences:</dt>
 <dd>Prints the version number of the first version with the CWD
     entry date, followed by a notation that there were no significant
     differences.</dd>
</dl>
<hr />
<hr />
""" % time.ctime())

# Find all current working versions of CTGovProtocols
qry = """
SELECT d.id
  FROM document d, doc_type t
 WHERE d.doc_type = t.id
   AND t.name = 'CTGovProtocol'
"""

try:
    cursor.execute(qry)
    docIds = [row[0] for row in cursor.fetchall()]
except cdrdb.Error, info:
    fatal("Unable to select documents to version:\n%s" % str(info))

# Counts
noVerCnt     = 0
noDateCnt    = 0
noEarlyCnt   = 0
diffVerCnt   = 0
noDiffVerCnt = 0
totalCnt     = 0

# Process each one
for docId in docIds:

    # DEBUG
    # if totalCnt >= 10: break

    # Full CDRnnnnnnnnnn form of doc id
    docIdStr = cdr.exNormalize(docId)[0]
    totalCnt += 1

    # Get info on versions
    (lastVer, lastPubVer, isChanged) = cdr.lastVersions(session, docIdStr)
    if (lastVer == -1):
        report("<h3>%s has no versions.</h3>" % docIdStr)
        noVerCnt += 1
        continue

    # Get the EntryDate for current working doc
    entryDate = getEntryDate(docIdStr, None)
    if not entryDate:
        report("<h3>%s has no PDQIndexing/EntryDate.</h3>" % docIdStr)
        noDateCnt += 1
        continue

    # Find first version that has this EntryDate
    checkVer = findCheckVersion(docIdStr, entryDate, lastVer)
    if not checkVer:
        report("<h3>%s[%s] has only earlier dated versions, " % \
               (docIdStr, entryDate) + "CWD must be current.</h3>")
        noEarlyCnt += 1
        continue

    # Do the diff
    diffText = diffDocs(docId, checkVer)
    if not diffText:
        report("<h3>%s[%s] is equivalent to " % (docIdStr, entryDate) \
             + "version: %d (of %d)</h3>" % (checkVer, lastVer))
        noDiffVerCnt += 1
    else:
        report("<h3>%s[%s] differences from version: %d (of %d)</h3>" % \
                (docIdStr, entryDate, checkVer, lastVer))
        report(diffText)
        diffVerCnt += 1


# Final report
report("""
<center>
<h2>Summary Statistics:</h2>

<table border='1'>
<tr>
 <th>Documents selected</th><td align='right' width='30'>%d</td>
</tr>
<tr>
 <th>Docs for which no versions exist</th><td align='right'>%d</td>
</tr>
<tr>
 <th>Docs with no (CWD) PDQIndexing/EntryDate</th><td align='right'>%d</td>
</tr>
<tr>
 <th>Docs with no earlier EntryDate'd versions</th><td align='right'>%d</td>
</tr>
<tr>
 <th>Docs with differences</th><td align='right'>%d</td>
</tr>
<tr>
 <th>Docs with no significant differences</th><td align='right'>%d</td>
</tr>
</table>
</center>
""" % (totalCnt, noVerCnt, noDateCnt, noEarlyCnt, diffVerCnt, noDiffVerCnt))

report("""
</body>
</html>
""")
rptf.close()
