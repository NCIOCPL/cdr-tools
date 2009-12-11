#----------------------------------------------------------------------
#
# $Id$
#
# Script for installing a new version of an XSL/T filter in the CDR.
#
#----------------------------------------------------------------------
import cdr, optparse, sys, cdrdb, re

#----------------------------------------------------------------------
# Find the filter document ID on the target server which matches the
# title found on the production server for the given production filter
# document ID.
#----------------------------------------------------------------------
def findTargetCdrId(prodCdrId, server):
    cursor = cdrdb.connect('CdrGuest', dataSource=cdr.PROD_HOST).cursor()
    cursor.execute("SELECT title FROM document WHERE id = ?", prodCdrId)
    title = cursor.fetchall()[0][0]
    cursor = cdrdb.connect('CdrGuest', dataSource=server).cursor()
    cursor.execute("""\
        SELECT d.id
          FROM document d
          JOIN doc_type t
            ON t.id = d.doc_type
         WHERE t.name = 'Filter'
           AND d.title = ?""", title)
    return cursor.fetchall()[0][0]

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
This program stores a new version of a filter on the target CDR server.

The default target server is the server on which the program is invoked.
The new version of the filter is obtained by reading the file named on
the command line, and the name of the file is expected to be in the format
"CDR9999999999.xml" where 9999999999 is the CDR ID of the filter as stored
on the production server.  The document ID of the filter for the target
server, if not provided as a command-line argument, is determined by
looking up the document's title on the production server using the document
ID extracted from the filename, and then looking up the filter document ID
matching that title on the target CDR server.  
It is common to provide the version control revision number of the 
filter in the comment option as well as the Bugzilla issue number, 
particularly when storing a new version of the filter on the production 
server.
   Sample comment:   R4321: Adding Vendor Info (Bug 1234) """)
    op.add_option("-s", "--server", default="localhost", help="target server")
    op.add_option("-i", "--docid", type="int", help="CDR ID on target server")
    op.add_option("-t", "--title", help="replacement title for filter")
    op.add_option("-v", "--version", default="Y", help="create version [Y/N]")
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
    if '.' not in options.server and 'localhost' not in options.server:
        options.server += cdr.DOMAIN_NAME
    if not options.docid:
        if options.server.upper() == cdr.PROD_HOST:
            options.docid = prodCdrId
        else:
            options.docid = findTargetCdrId(prodCdrId, options.server)

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
    session = cdr.login(uid, pwd, options.server)
    checkForProblems(session, op)

    #------------------------------------------------------------------
    # 4. Check out the document from the target CDR server.
    #------------------------------------------------------------------
    cdrId = "CDR%010d" % options.docid
    docObj = cdr.getDoc(session, cdrId, checkout='Y', host=options.server,
                        getObject=True)
    checkForProblems(docObj, op)

    #------------------------------------------------------------------
    # 5. Store the new version on the target CDR server.
    #------------------------------------------------------------------
    docObj.xml = docXml
    if options.title:
        docObj.ctrl['DocTitle'] = options.title
    doc = str(docObj)
    cdrId = cdr.repDoc(session, doc=doc, host=options.server, checkIn="Y",
                       reason=options.comment, comment=options.comment,
                       ver=options.version, verPublishable="N", setLinks="N")
    checkForProblems(cdrId, op)

    #------------------------------------------------------------------
    # 6. Report the number of the new version.
    #------------------------------------------------------------------
    versions = cdr.lastVersions(session, cdrId, options.server)
    print "stored version %d of filter %d on %s" % (versions[0],
                                                    options.docid,
                                                    options.server)

if __name__ == '__main__':
    main()
