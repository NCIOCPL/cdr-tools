#----------------------------------------------------------------------
#
# $Id$
#
# Script for changing a CDR filter document.  Must be used on each
# tier where the filter exists in order to bring the filter titles
# on all tiers in sync.  Changing a filter title should be rare,
# except perhaps in the very early stages of a new filter, since
# once a filter is in production there is like to be other software
# which relies on the stability of that filter's title.
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
    op = optparse.OptionParser(usage="%prog [options] UID PWD CDRID FILE",
                               description="""\
This program changes the title of a CDR filter document.  To use the program,
you must first change the filter title comment embedded in the document file
named as the final argument to the script.  That comment has the format:

  <!-- Filter title: FILTER-TITLE -->

The program will extract the title from that comment, strip leading and
trailing whitespace, and replace the document title stored in the CDR
for the filter with this new title.

IMPORTANT: You must use this script on ALL tiers where the filter has
been installed to make the filter's title match on all the servers.

Changing a filter title should be rare, except perhaps in the very early
stages of development for a new filter, since once a filter is in production,
there will likely be a body of software which relies on the stability of
the filter's title.""")

    op.add_option("-v", "--version", default="Y", help="create version [Y/N]")
    op.add_option("-p", "--publishable", default="N",
                  help="create pub version [Y/N]")
    op.add_option("-c", "--comment", help="description of new version",
                  default="")
    return op

#----------------------------------------------------------------------
# Extract the filter title from the document.
#----------------------------------------------------------------------
def getNewTitle(doc):

    match = re.search("<!--\\s*filter title:(.*?)-->", doc, re.I)
    if not match:
        raise Exception("Filter title comment not found")
    title = match.group(1).strip()
    if not title:
        raise Exception("Filter title in document comment is empty")
    return title

#----------------------------------------------------------------------
# Store the new version of the filter.  Processing steps:
#
#  1. Parse the command-line options and arguments.
#  2. Load the new version of the filter from the file system.
#  3. Log into the CDR on the target server.
#  4. Check out the document from the target CDR server.
#  5. Plug in the new title for the filter.
#  6. Store the new version on the target CDR server.
#  7. Report the number of the new version.
#
#----------------------------------------------------------------------
def main():

    #------------------------------------------------------------------
    # 1. Parse the command-line options and arguments.
    #------------------------------------------------------------------
    op = createOptionParser()
    (options, args) = op.parse_args()
    if len(args) != 4:
        op.error("incorrect number of arguments")
    uid, pwd, idArg, filename = args
    if not options.publishable:
        options.publishable = 'N'
    elif options.publishable == 'Y':
        options.version = 'Y'
    fullId, intId, fragId = cdr.exNormalize(idArg)

    # If no comment is specified the last comment used (from the
    # all_docs table) would be stored.
    # Setting the comment to something to overwrite the last comment
    # -----------------------------------------------------------------
    if not options.comment:
        options.comment = "Filter title changed"

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
    docObj = cdr.getDoc(session, fullId, checkout='Y', getObject=True)
    checkForProblems(docObj, op)

    #------------------------------------------------------------------
    # 5. Plug in the new title for the filter.
    #------------------------------------------------------------------
    docObj.ctrl['DocTitle'] = getNewTitle(docXml)

    #------------------------------------------------------------------
    # 6. Store the new version on the target CDR server.
    #------------------------------------------------------------------
    doc = str(docObj)
    print 'Versioned: %s, Publishable: %s' % (options.version,
                                              options.publishable)
    cdrId = cdr.repDoc(session, doc=doc, checkIn="Y", setLinks="N",
                       reason=options.comment, comment=options.comment,
                       ver=options.version, verPublishable=options.publishable)
    checkForProblems(cdrId, op)

    #------------------------------------------------------------------
    # 7. Report the number of the latest version.
    #------------------------------------------------------------------
    versions = cdr.lastVersions(session, cdrId)
    if options.version == "N":
        print "CWD for %s updated" % cdrId
    else:
        print "Latest version of %s is %d" % (cdrId, versions[0])
    print ""
    print "DON'T FORGET TO CHANGE THE TITLE OF THIS FILTER ON ALL TIERS!"

if __name__ == '__main__':
    main()
