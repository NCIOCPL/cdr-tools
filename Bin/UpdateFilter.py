#----------------------------------------------------------------------
#
# $Id$
#
# Script for installing a new version of an XSL/T filter in the CDR.
#
# JIRA::OCECDR-3694
#
#----------------------------------------------------------------------
import cdr, optparse, sys, cdrdb, re

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

#----------------------------------------------------------------------
# Create an object which can describe the behavior of this command
# and the options and arguments accepted/required.
#----------------------------------------------------------------------
def createOptionParser():
    op = optparse.OptionParser(usage="%prog [options] UID PWD FILE",
                               description="""\
This program stores a new version of a filter on the CDR server.

The new version of the filter is obtained by reading the file named on
the command line, and the name of the file is expected to be in the format
"CDR9999999999.xml" where 9999999999 is the CDR ID of the filter as stored
on the production server.  If the document ID for the filter is different
on the tier on which this script is being run from the filter's ID on the
production tier, the document ID for the filter on the non-production tier
must be supplied on the command line.

It is common to provide the version control revision number of the 
filter in the comment option as well as the Bugzilla issue number, 
particularly when storing a new version of the filter on the production 
server.

   Sample comment:   R4321 (Bug 1234): Adding Vendor Info""")

    op.add_option("-i", "--docid", type="int", help="CDR ID on target server")
    op.add_option("-t", "--title", help="replacement title for filter")
    op.add_option("-v", "--version", default="Y", help="create version [Y/N]")
    op.add_option("-p", "--publishable", default="N",
                  help="create pub version [Y/N]")
    op.add_option("-c", "--comment", help="description of new version",
                  default="")
    return op

#----------------------------------------------------------------------
# Store the new version of the filter.  Processing steps:
#
#  1. Parse the command-line options and arguments.
#  2. Load the new version of the filter from the file system.
#  3. Log into the CDR on the target server.
#  4. Check out the document from the target CDR server.
#  5. Store the new version on the target CDR server.
#  6. Report the number of the new version.
#
#----------------------------------------------------------------------
def main():

    #------------------------------------------------------------------
    # 1. Parse the command-line options and arguments.
    #------------------------------------------------------------------
    op = createOptionParser()
    (options, args) = op.parse_args()
    if len(args) != 3:
        op.error("incorrect number of arguments")
    uid, pwd, filename = args
    prodCdrId = int(re.sub("[^\\d]+", "", filename))
    if not options.docid:
        options.docid = prodCdrId
    if not options.publishable:
        options.publishable = 'N'
    elif options.publishable == 'Y':
        options.version = 'Y'

    # If no comment is specified the last comment used (from the
    # all_docs table) would be stored.
    # Setting the comment to something to overwrite the last comment
    # -----------------------------------------------------------------
    if not options.comment:
        options.comment = 'Replaced w/o user comment'

    #------------------------------------------------------------------
    # 2. Load the new version of the filter from the file system.
    #------------------------------------------------------------------
    fp = open(filename, 'r')
    docXml = fp.read()
    fp.close()
    if u']]>' in docXml:
        op.error("CdrDoc wrapper must be stripped from the file")

    #------------------------------------------------------------------
    # 3. Log into the CDR on the target server.
    #------------------------------------------------------------------
    session = cdr.login(uid, pwd)
    checkForProblems(session, op)

    #------------------------------------------------------------------
    # 4. Check out the document from the target CDR server.
    #------------------------------------------------------------------
    cdrId = "CDR%010d" % options.docid
    docObj = cdr.getDoc(session, cdrId, checkout='Y', getObject=True)
    checkForProblems(docObj, op)

    #------------------------------------------------------------------
    # 5. Store the new version on the target CDR server.
    #------------------------------------------------------------------
    docObj.xml = docXml
    
    if options.title:
        docObj.ctrl['DocTitle'] = options.title
    doc = str(docObj)
    print 'Versioned: %s, Publishable: %s' % (options.version,
                                              options.publishable)

    cdrId = cdr.repDoc(session, doc=doc, checkIn="Y", setLinks="N",
                       reason=options.comment, comment=options.comment,
                       ver=options.version, verPublishable=options.publishable)
    checkForProblems(cdrId, op)

    #------------------------------------------------------------------
    # 6. Report the number of the new version.
    #------------------------------------------------------------------
    versions = cdr.lastVersions(session, cdrId)
    print "stored version %d of filter %d" % (versions[0], options.docid)

if __name__ == '__main__':
    main()
