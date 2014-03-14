#----------------------------------------------------------------------
#
# $Id$
#
# Script for installing a new version of a CDR publishing control document.
#
# Example usage:
#   UpdatePubControlDoc.py -p Y -c OCECDR-99999 elmer vewy-secwet Primary.xml
#
#----------------------------------------------------------------------
import cdr, optparse, sys, cdrdb, re, os

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
This program stores a new version of a publishing control on the CDR server.

The new version of the document is obtained by reading the file named on
the command line, and the name of the file is expected to be in the format
"NAME.xml" where NAME is the name of the publishing system (e.g., Primary,
Mailers, or QcFilter).

It is common to provide the version control revision number of the 
document in the comment option as well as the JIRA ticket number, 
particularly when storing a new version of the document on the production 
server.

   Sample comment:   R54321 (JIRA::OCECDR-9999): New mailer type""")

    op.add_option("-v", "--version", default="Y", help="create version [Y/N]")
    op.add_option("-p", "--publishable", default="N",
                  help="create pub version [Y/N]")
    op.add_option("-c", "--comment", help="description of new version",
                  default="")
    return op

#----------------------------------------------------------------------
# Extract the document title from the filename, and look up the CDR
# document ID which matches the title.
#----------------------------------------------------------------------
def getDocId(path):

    # Extract the document title.
    basename = os.path.basename(path)
    if not basename.lower().endswith(".xml"):
        raise Exception("unexpected filename pattern %s" % repr(path))
    title = basename[:-4]
    query = cdrdb.Query("document d", "d.id")
    query.join("doc_type t", "t.id = d.doc_type")
    query.where("t.name = 'PublishingSystem'")
    query.where("d.title = ?", title)
    rows = query.execute().fetchall()
    if not rows:
        raise Exception(u"Control document %s not found" % repr(title))
    if len(rows) > 1:
        raise Exception(u"Ambiguous title %s" % repr(title))
    return rows[0][0]

#----------------------------------------------------------------------
# Store the new version of the control document.  Processing steps:
#
#  1. Parse the command-line options and arguments.
#  2. Load the new version of the control document from the file system.
#  3. Find the CDR ID which matches the control document title
#  4. Log into the CDR on the target server.
#  5. Check out the document from the target CDR server.
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
    if len(args) != 3:
        op.error("incorrect number of arguments")
    uid, pwd, filename = args
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
    # 2. Load the new version of the control document from the file system.
    #------------------------------------------------------------------
    fp = open(filename, 'r')
    docXml = fp.read()
    fp.close()
    if u']]>' in docXml:
        op.error("CdrDoc wrapper must be stripped from the file")

    #------------------------------------------------------------------
    # 3. Find out what the control document's document ID is.
    #------------------------------------------------------------------
    docId = getDocId(filename)

    #------------------------------------------------------------------
    # 4. Log into the CDR on the target server.
    #------------------------------------------------------------------
    session = cdr.login(uid, pwd)
    checkForProblems(session, op)

    #------------------------------------------------------------------
    # 5. Check out the document from the target CDR server.
    #------------------------------------------------------------------
    cdrId = "CDR%010d" % docId
    docObj = cdr.getDoc(session, cdrId, checkout='Y', getObject=True)
    checkForProblems(docObj, op)

    #------------------------------------------------------------------
    # 6. Store the new version on the target CDR server.
    #------------------------------------------------------------------
    docObj.xml = docXml
    doc = str(docObj)
    print 'Versioned: %s, Publishable: %s' % (options.version,
                                              options.publishable)
    cdrId = cdr.repDoc(session, doc=doc, checkIn="Y", val="Y",
                       reason=options.comment, comment=options.comment,
                       ver=options.version, verPublishable=options.publishable)
    checkForProblems(cdrId, op)

    #------------------------------------------------------------------
    # 7. Report the number of the latest version.
    #------------------------------------------------------------------
    if options.version == "N":
        print "CWD for %s updated" % cdrId
    else:
        versions = cdr.lastVersions(session, cdrId)
        print "Latest version of %s is %d" % (cdrId, versions[0])

if __name__ == '__main__':
    main()
