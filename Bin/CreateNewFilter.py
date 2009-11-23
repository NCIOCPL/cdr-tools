#----------------------------------------------------------------------
#
# $Id$
#
# Creates a new stub filter document on Bach.  See description below in
# createOptionParser.
#
#----------------------------------------------------------------------
import cdr, optparse, sys, cgi

#----------------------------------------------------------------------
# Create an object which can describe the behavior of this command
# and the options and arguments accepted/required.
#----------------------------------------------------------------------
def createOptionParser():
    op = optparse.OptionParser(usage='%prog [options] UID PWD "TITLE"',
                               description="""\
This program creates a new stub filter document on Bach.  A file is created
in the current working directory containing the XML content for the stub
document under the name CDR9999999999.xml (where 9999999999 is replaced
by the actual 10-digit version of the newly created document's CDR ID).
This document can be edited and installed in the version control system.""")
    op.add_option("-s", "--server", default=cdr.PROD_HOST, help="for debugging")
    return op

#----------------------------------------------------------------------
# Find out if the response to a CDR client-server command indicates
# failure.  If so, describe the problem and exit.  Note that this
# function works properly even when passed a document object, because
# cdr.getErrors() only looks for error messages if a string is passed
# for the first argument.
#----------------------------------------------------------------------
def checkForProblems(response, optionsParser):
    errors = cdr.getErrors(response, errorsExpected = False, asSequence = True)
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
    session = cdr.login(uid, pwd, options.server)
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
    cdrId = cdr.addDoc(session, doc = doc, host = options.server)
    checkForProblems(cdrId, op)
    response = cdr.unlock(session, cdrId, host = options.server)
    checkForProblems(response, op)
    name = cdrId + ".xml"
    fp = open(name, "w")
    fp.write(stub)
    fp.close()
    print "Created %s" % name
    cdr.logout(session, host = options.server)

if __name__ == '__main__':
    main()
