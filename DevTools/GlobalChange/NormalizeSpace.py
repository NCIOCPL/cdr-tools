#----------------------------------------------------------------------
#
# $Id$
#
# Utility for normalizing whitespace in specified fields for a
# specified CDR document type, using a global change.
#
# Command line:
#   See usage() below.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------

import sys, re, cdr, cdrdb, ModifyDocs

# Globals initialized in main, before ModifyDocs class methods are invoked
docTypeToGet  = None
xsltTransform = None
docCount      = 9999999

#-------------------------------------------------------------
# This XSLT transform will copy all components of a document
# to the output, normalizing space in named elements or attributes
# along the way.
#
# To use it, the program must concatenate the following:
#   CHANGE_TEMPLATE1
#   One or more copies of CHANGE_TEMPLATE_ELEM or _ATTR with %s's interpolated.
#   "</xsl:transform>"
#-------------------------------------------------------------
CHANGE_TEMPLATE1=\
"""<?xml version="1.0"?>
 <xsl:transform xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                version="1.0"
                xmlns:cdr="cips.nci.nih.gov/cdr">
<xsl:template match='@*|node()|comment()|processing-instruction()'>
  <xsl:copy>
    <xsl:apply-templates select='@*|node()|comment()|processing-instruction()'/>
  </xsl:copy>
</xsl:template>
"""

CHANGE_TEMPLATE_ELEM="""
<xsl:template match='%s'>
  <xsl:choose>
    <xsl:when test='normalize-space(.)!=.'>
      <xsl:element name='%s'>
        <xsl:value-of select='normalize-space(.)'/>
      </xsl:element>
    </xsl:when>
    <xsl:otherwise>
      <xsl:copy-of select='.'/>
    </xsl:otherwise>
  </xsl:choose>
</xsl:template>
"""

CHANGE_TEMPLATE_ATTR="""
<xsl:template match='%s'>
  <xsl:choose>
    <xsl:when test='normalize-space(.)!=.'>
      <xsl:attribute name='%s'>
        <xsl:value-of select='normalize-space(.)'/>
      </xsl:attribute>
    </xsl:when>
    <xsl:otherwise>
      <xsl:copy-of select='.'/>
    </xsl:otherwise>
  </xsl:choose>
</xsl:template>
"""

#----------------------------------------------------------------------
# Filter class for ModifyDocs.Job object.
#
# getDocIds() retrieves a list of CDR document IDs to test and
# normalize.
#----------------------------------------------------------------------
class Filter:
    def getDocIds(self):
        """
        Retrieve all of the doc ids for the doctype reference on
        the command line.
        """
        global docTypeToGet

        conn = cdrdb.connect('CdrGuest')
        cursor = conn.cursor()
        cursor.execute("""\
         SELECT TOP %d d.id
           FROM document d
           JOIN doc_type t
             ON d.doc_type = t.id
          WHERE t.name = '%s'
          ORDER BY d.id
        """ % (docCount, docTypeToGet))

        # Return list of first element of each row
        return [row[0] for row in cursor.fetchall()]

#----------------------------------------------------------------------
# The Transform class is given to the ModifyDocs.Job object, which in
# turn gives it to each ModifyDocs.Doc object.  The run() method of
# this class takes a cdr.Doc object and returns a (possibly) modified
# copy of that object's xml member.
#----------------------------------------------------------------------
class Transform:
    def run(self, docObj):

        # Filter using the xsltTransform constructed in __main__
        response = cdr.filterDoc('guest', xsltTransform,
                                  doc = docObj.xml, inline = 1)
        if type(response) in (type(""), type(u"")):
            raise Exception("Failure in transformation Filter: %s" % response)

        # Return the possibly changed doc
        # ModifyDocs will do the right thing, only saving it if changed.
        return response[0]

#----------------------------------------------------------------------
# Create XSLT transform
#----------------------------------------------------------------------
def createTransform(fileName):
    """
    Create a transform according to the rules explained above the
    definition of CHANGE_TEMPLATE1.

    Only the specific elements or attributes listed in fileName will
    be normalized.

    The constructed transform is stored in the global xsltTransform.

    Pass:
        Name of file containing XPaths, one per line, e.g.,
            /Term/PreferredName
            /Term/OtherName/OtherTermName
            /Term/OtherName/OtherNameType
            /Term/OtherName/SourceInformation
            ...
    """
    global xsltTransform

    try:
        fp = open(fileName)
    except IOError, info:
        sys.stderr.write("Unable to open %s\n" % fileName)
        sys.stderr.write(str(info))
        sys.stderr.write("\nAborting.\n")
        sys.exit(1)

    # Construct transform
    xsltTransform = CHANGE_TEMPLATE1

    done = False
    while not done:
        line = fp.readline()
        if not line:
            done = True
        else:
            # Possibly fully qualified XPath
            line = line.strip()

            # Delete '#' delimited comments
            xpath = re.sub(r" *#.*$", '', line)

            # If anything left
            if xpath:
                # Individual QName of the last element on the path
                qName = xpath.split('/')[-1:][0]

                # Add appropriate template for element or attribute
                if qName[0] == '@':
                    xsltTransform += CHANGE_TEMPLATE_ATTR % (xpath, qName[1:])
                else:
                    xsltTransform += CHANGE_TEMPLATE_ELEM % (xpath, qName)

    xsltTransform += "\n</xsl:transform>\n"

    # Debugging
    fp = open("NormSpace.xsl", "w")
    fp.write(xsltTransform)
    fp.close()

#----------------------------------------------------------------------
# Usage
#----------------------------------------------------------------------
def usage(msg):
    """
    Display usage message and quit.

    Pass:
        msg  - If not None, display this error message first.
    """
    if msg:
        sys.stderr.write("%s\n\n" % msg)

    sys.stderr.write("""
usage: normalizeSpace.py userid, pw doctype fieldNameListPath {'run' | count}

    Reads all documents of type 'doctype'.

    For each one:

        Reads all fully qualified XPaths in the file named by
        "fieldNameListPath".  Place one XPath on each line.

        Passes each such field through the XSLT normalize-space()
        function to eliminate leading and trailing whitespace and to
        normalize all internal whitespace to single spaces.

        Uses ModifyDocs to handle versioning, test mode, etc.

    If 'run' specified on command line, writes modified documents back
    to the database.  Else just outputs to the global change output
    directory.

    If integer count specified on command line, process 'count' document
    in test mode.

    The generated template is written to ./NormSpace.xsl, overwriting whatever
    may be there.  count==0 generates a template without processing any
    documents.
""")

if __name__ == "__main__":

    # Command line
    if len(sys.argv) < 5:
        usage("Insufficient arguments");
        sys.exit(1)

    # Set test mode
    testMode = True
    if len(sys.argv) > 5:
        if sys.argv[5] == 'run':
            testMode = False
        else:
            docCount = int(sys.argv[5])

    # Construct transform or exit with error
    createTransform(sys.argv[4])

    # Set document type for selections
    docTypeToGet = sys.argv[3]

    # Modify the documents
    job = ModifyDocs.Job(sys.argv[1], sys.argv[2], Filter(), Transform(),
          "Global change normalizing whitespace.", testMode=testMode)
    job.run()
