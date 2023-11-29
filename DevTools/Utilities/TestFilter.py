#!/usr/bin/env python3
###########################################################
# Test filter a CDR doc from the command line.
#
# Run without args for usage info.
###########################################################

import sys
import getopt
import cdr
from cdrapi import db
from datetime import datetime

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

# For trace messages - courtesy of Oliver Becker, Humboldt U. Berlin
# http://www2.informatik.hu-berlin.de/~obecker/XSLT/
# 2021-12-31: added string splicing to comply with PEP-8 on line lengths.
TRACE_FILTER = """<?xml version="1.0"?>

<!--
   Trace utility, modifies a stylesheet to produce trace messages
   Version 0.2
   LGPL (c) Oliver Becker, 2002-02-13
   obecker@informatik.hu-berlin.de
-->

<xsl:transform version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:trace="http://www.obqo.de/XSL/Trace"
  xmlns:alias="http://www.w3.org/TransformAlias"
  exclude-result-prefixes="alias">

  <xsl:namespace-alias stylesheet-prefix="alias" result-prefix="xsl" />

  <!-- <xsl:output indent="yes" /> -->

  <!-- XSLT root element -->
  <xsl:template match="xsl:stylesheet | xsl:transform">
    <xsl:copy>
      <!-- We need the trace namespace for names and modes -->
      <xsl:copy-of select="document('')/*/namespace::trace" />
      <!-- dito: perhaps a namespace was used only as attribute value -->
      <xsl:copy-of select="namespace::*|@*" />
      <xsl:apply-templates />
      <!-- append utility templates -->
      <xsl:copy-of
           select="document('')/*/xsl:template
                                  [@mode='trace:getCurrent' or
                                   @name='trace:getPath']" />
      <!-- compute the lowest priority and add a default template with
           a lower priority for element nodes -->
      <xsl:variable name="priority"
                    select="xsl:template/@priority
                            [not(. &gt; current()/xsl:template/@priority)]" />
      <xsl:variable name="newpri">
        <xsl:choose>
          <xsl:when test="$priority &lt; -1">
            <xsl:value-of select="$priority - 1" />
          </xsl:when>
          <!-- in case there's only a greater or no priority at all -->
          <xsl:otherwise>-2</xsl:otherwise>
        </xsl:choose>
      </xsl:variable>
      <!-- copy the contents only -->
      <alias:template match="*" priority="{$newpri}">
        <xsl:copy-of select="document('')/*/xsl:template
                             [@name='trace:defaultRule']/node()" />
      </alias:template>
    </xsl:copy>
  </xsl:template>


  <!-- XSLT templates -->
  <xsl:template match="xsl:template">
    <xsl:copy>
      <xsl:copy-of select="@*" />
      <!-- first: copy parameters -->
      <xsl:apply-templates select="xsl:param" />
      <alias:param name="trace:callstack" />
      <xsl:choose>
        <xsl:when test="@name">
          <alias:variable name="trace:current"
                          select="concat($trace:callstack,'/{@name}')" />
        </xsl:when>
        <xsl:otherwise>
          <alias:variable name="trace:current"
                 select="concat($trace:callstack,
                         '/{count(preceding-sibling::xsl:template)+1}')" />
        </xsl:otherwise>
      </xsl:choose>

      <!-- emit a message -->
      <alias:message>
        <alias:call-template name="trace:getPath" />
        <alias:text>&#xA;   stack: </alias:text>
        <alias:value-of select="$trace:current" />
        <xsl:if test="@match or @mode">
          <alias:text> (</alias:text>
          <xsl:if test="@match">
            <alias:text>match="<xsl:value-of select="@match" />"</alias:text>
            <xsl:if test="@mode">
              <alias:text><xsl:text> </xsl:text></alias:text>
            </xsl:if>
          </xsl:if>
          <xsl:if test="@mode">
            <alias:text>mode="<xsl:value-of select="@mode" />"</alias:text>
          </xsl:if>
          <alias:text>)</alias:text>
        </xsl:if>
        <xsl:apply-templates select="xsl:param" mode="traceParams" />
      </alias:message>

      <!-- process children except parameters -->
      <xsl:apply-templates select="node()[not(self::xsl:param)]" />
    </xsl:copy>
  </xsl:template>


  <!-- add the callstack parameter for apply-templates and call-template -->
  <xsl:template match="xsl:apply-templates | xsl:call-template">
    <xsl:copy>
      <xsl:copy-of select="@*" />
      <alias:with-param name="trace:callstack" select="$trace:current" />
      <xsl:apply-templates />
    </xsl:copy>
  </xsl:template>


  <!-- output parameter values -->
  <xsl:template match="xsl:param" mode="traceParams">
    <alias:text>&#xA;   param: """ """\
name="<xsl:value-of select="@name" />" value="</alias:text>
    <alias:value-of select="${@name}" />" <alias:text />
    <!--
    <alias:copy-of select="${@name}" />" <alias:text />
    -->
  </xsl:template>

  <!-- output variable values -->
  <xsl:template match="xsl:variable">
    <xsl:copy>
      <xsl:copy-of select="@*" />
      <xsl:apply-templates />
    </xsl:copy>
    <xsl:if test="ancestor::xsl:template">
      <alias:message>   variable: """ """\
name="<xsl:value-of select="@name" />" value="<alias:text />
      <alias:value-of select="${@name}" />" </alias:message>
    </xsl:if>
  </xsl:template>

  <!-- copy every unprocessed node -->
  <xsl:template match="*|@*">
    <xsl:copy>
      <xsl:apply-templates select="@*" />
      <xsl:apply-templates />
    </xsl:copy>
  </xsl:template>


  <!-- ******************************************************************* -->
  <!-- The following templates will be copied into the modified stylesheet -->
  <!-- ******************************************************************* -->

  <!--
   | trace:getPath
   | compute the absolute path of the context node
   +-->
  <xsl:template name="trace:getPath">
    <xsl:text>node: </xsl:text>
    <xsl:for-each select="ancestor::*">
      <xsl:value-of
           select="concat('/', name(), '[',
           count(preceding-sibling::*[name()=name(current())])+1, ']')" />
    </xsl:for-each>
    <xsl:apply-templates select="." mode="trace:getCurrent" />
  </xsl:template>


  <!--
   | trace:getCurrent
   | compute the last step of the location path, depending on the
   | node type
   +-->
  <xsl:template match="*" mode="trace:getCurrent">
    <xsl:value-of
         select="concat('/', name(), '[',
         count(preceding-sibling::*[name()=name(current())])+1, ']')" />
  </xsl:template>

  <xsl:template match="@*" mode="trace:getCurrent">
    <xsl:value-of select="concat('/@', name())" />
  </xsl:template>

  <xsl:template match="text()" mode="trace:getCurrent">
    <xsl:value-of
        select="concat('/text()[', count(preceding-sibling::text())+1, ']')" />
  </xsl:template>

  <xsl:template match="comment()" mode="trace:getCurrent">
    <xsl:value-of
         select="concat('/comment()[',
                        count(preceding-sibling::comment())+1, ']')" />
  </xsl:template>

  <xsl:template match="processing-instruction()" mode="trace:getCurrent">
    <xsl:value-of
         select="concat('/processing-instruction()[',
         count(preceding-sibling::processing-instruction())+1, ']')" />
  </xsl:template>


  <!--
   | trace:defaultRule
   | default rule with parameter passing
   +-->
  <xsl:template name="trace:defaultRule">
    <xsl:param name="trace:callstack" />
    <xsl:message>
      <xsl:call-template name="trace:getPath" />
      <xsl:text>&#xA;   default rule applied</xsl:text>
    </xsl:message>
    <xsl:apply-templates>
      <xsl:with-param name="trace:callstack" select="$trace:callstack" />
    </xsl:apply-templates>
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
    except IOError as info:
        sys.stderr.write(str(info))
        sys.exit(1)
    return text


def stripMsgNoise(msgText):
    """
    Remove strings that our XSLT processor adds to messages that
    appear on every message.  These are unwanted in trace debugging
    because they can appear on hundreds of lines

    Pass:
        Text of the messages to be stripped.

    Return:
        Stripped text.
    """
    # warnPat = re.compile(r"^  Warning \[.*\]?")

    # Treat each line
    msgLines = msgText.split("\n")
    newLines = []
    for line in msgLines:
        # Delete processor Warning lines
        # line = warnPat.sub("", line)
        # if line.startswith("  Warning "): continue

        # Normalize whitespace
        words = line.split()
        newLines.append(" ".join(words))

    # Return transform as a single string
    return ("\n".join(newLines))


# Option defaults
fullOutput = True
indentOutput = False
traceDbg = False

# Option overrides from command line
opts, args = getopt.getopt(sys.argv[1:], "ipt")
for opt in opts:
    if opt[0] == '-i':
        indentOutput = True
    if opt[0] == '-p':
        fullOutput = False
    if opt[0] == '-t':
        traceDbg = True

# usage
if len(args) < 2:
    sys.stderr.write("""
usage: TestFilter.py {opts} Doc Filter {"parm=data..." {"parm=data ..."} ...}

 Options:
   -i = Indent output document (pretty print).
   -p = Plain output, just the filtered document, no banners or messages.
   -t = Perform XSLT trace using O. Becker's tracer.

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
    int(filter)
except ValueError:
    # Filter was not specified as a document ID.
    # It may be a filename or a "name:" or "set:" CDR identifier
    if filter.startswith("file:"):
        filter = getFileContent(filter[5:])
        inline = True
    elif filter.startswith("name:") or filter.startswith("set:"):
        # Can't filter a set with tracing at this time
        if filter.startswith("set:") and traceDbg:
            sys.stderr.write("Can't trace through a set.  Sorry.")
            sys.exit(1)
    else:
        sys.stderr.write('Filter identifier "%s" not recognized' % filter)
        sys.exit(1)

# Session id for access to server filtering
session = "guest"

# If tracing requested, filter the filter to add tracing
if traceDbg:
    # If filter is in database, have to fetch it
    if not inline:
        # Filter supplied by title
        if isinstance(filter, str):
            # Strip off "name:" that we know must be there
            filterTitle = filter[5:]

            # Fetch filter xml from the database, fail if exception
            conn = db.connect()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT xml
                  FROM document d
                  JOIN doc_type t
                    ON d.doc_type = t.id
                 WHERE d.title = ?
                   AND t.name = 'Filter'
            """, (filterTitle,))
            row = cursor.fetchone()
            if not row:
                sys.stderr.write("Unable to find filter '%s'" % filter)
                sys.exit(1)

        # Else filter supplied by CDR doc id
        else:
            # Fetch filter xml from the database, fail if exception
            conn = db.connect()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT xml
                  FROM document
                 WHERE id = ?
            """, (filter,))
            row = cursor.fetchone()
            if not row:
                sys.stderr.write("Unable to find filter '%s'" % filter)
                sys.exit(1)

        # Replace name with actual filter for use inline
        filter = row[0]
        inline = True

    # Transform the caller requested filter to incorporate tracing
    resp = cdr.filterDoc(session, filter=TRACE_FILTER, doc=filter,
                         inline=True)
    if type(resp) in (type(""), type(u"")):
        sys.stderr.write("Error adding tracing to filter:\n  %s" % resp)
        sys.exit(1)

    # Substitute transformed filter for original
    filter = resp[0]

# Gather optional parms
parms = []
argx = 2
while argx < len(args):
    parms.append(args[argx].split('='))
    argx += 1

# Filter identifier strings should be in list format for cdr.filterDoc()
if not inline:
    filter = [filter]

# Filter doc
startClock = datetime.now()
resp = cdr.filterDoc(session, filter=filter, docId=docId, doc=doc,
                     inline=inline, parm=parms)
stopClock = datetime.now()

if type(resp) in (type(""), type(u"")):
    sys.stderr.write("Error response:\n  %s" % resp)
    sys.exit(1)

(xml, msgs) = resp

# If we're tracing, compact the messages a bit
if traceDbg:
    msgs = stripMsgNoise(msgs)

# If pretty printing with indentation
if indentOutput:
    resp = cdr.filterDoc(session, filter=INDENT_FILTER, doc=xml, inline=True)
if isinstance(resp, str):
    sys.stderr.write(f"Unable to indent output:\n  {resp}\n--- continuing:\n")
else:
    xml = resp[0]

# Output to stdout
if fullOutput:
    print(("""
RESPONSE FROM HOST:  cdr.filterDoc time = %f seconds
DOCUMENT
----------------------------------
%s
----------------------------------

MESSAGES
----------------------------------
%s
----------------------------------
""" % ((stopClock - startClock).total_seconds(), xml, msgs)))

else:
    print((resp[0]))
