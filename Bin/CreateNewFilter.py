#----------------------------------------------------------------------
#
# $Id$
#
# Creates a new stub filter document in the CDR.  See description below
# in createOptionParser.
#
# OCECDR-3694
#
#----------------------------------------------------------------------
import cdr, optparse, sys, cgi

#----------------------------------------------------------------------
# Create an object which can describe the behavior of this command
# and the options and arguments accepted/required.
#----------------------------------------------------------------------
def createOptionParser():
    op = optparse.OptionParser(usage='%prog UID PWD "TITLE"',
                               description="""\
This program creates a new stub filter document in the CDR.  The program
is intended to be run on the production server to get the CDR ID to be
used for the filter's version control file name (though it can be run
on lower tiers for testing).  A file is created in the current working
directory containing the XML content for the stub document under the
name CDR9999999999.xml (where 9999999999 is replaced by the actual
10-digit version of the newly created document's CDR ID).  This document
can be edited and installed in the version control system.

Enclose the title argument in double quote marks if it contains any
embedded spaces (which it almost certainly will).  The filter title
will be included in the document as an XML comment, and therefore
cannot contain the substring --.""")
    return op

#----------------------------------------------------------------------
# Find out if the response to a CDR client-server command indicates
# failure.  If so, describe the problem and exit.  Note that this
# function works properly even when passed a document object, because
# cdr.getErrors() only looks for error messages if a string is passed
# for the first argument.
#----------------------------------------------------------------------
def checkForProblems(response, optionsParser):
    errors = cdr.getErrors(response, errorsExpected=False, asSequence=True)
    if errors:
        for error in errors:
            sys.stderr.write("%s\n" % error)
        optionsParser.error("aborting")

def main():
    op = createOptionParser()
    (options, args) = op.parse_args()
    if len(args) != 3:
        op.print_help()
        op.exit(2)
    uid, pwd, title = args
    title = title.strip()
    if not title:
        sys.stderr.write("Empty title argument.\n")
        op.print_help()
        op.exit(2)
    if "--" in title:
        sys.stderr.write("Filter title cannot contain --\n")
        op.print_help()
        op.exit(2)
    session = cdr.login(uid, pwd)
    checkForProblems(session, op)
    stub = """\
<?xml version='1.0' encoding='utf-8'?>
<!-- $""" """Id$ -->
<!-- Filter title: %s -->
<xsl:transform               xmlns:xsl = 'http://www.w3.org/1999/XSL/Transform'
                             xmlns:cdr = 'cips.nci.nih.gov/cdr'
                               version = '1.0'>

 <xsl:output                    method = 'xml'
                              encoding = 'utf-8'/>

 <xsl:param                       name = 'sample-param'
                                select = '"default-value"'/>

 <!-- Sample template -->
 <xsl:template                   match = '@*|node()'>
  <xsl:copy>
   <xsl:apply-templates         select = '@*|node()'/>
  </xsl:copy>
 </xsl:template>

</xsl:transform>
""" % cgi.escape(title)
    docObj = cdr.Doc(stub, 'Filter', { 'DocTitle': title })
    doc = str(docObj)
    cdrId = cdr.addDoc(session, doc=doc)
    checkForProblems(cdrId, op)
    response = cdr.unlock(session, cdrId)
    checkForProblems(response, op)
    name = cdrId + ".xml"
    fp = open(name, "wb")
    fp.write(stub)
    fp.close()
    print "Created %s" % name
    cdr.logout(session)

if __name__ == '__main__':
    main()
