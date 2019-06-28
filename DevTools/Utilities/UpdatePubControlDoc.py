#!/usr/bin/env python
#----------------------------------------------------------------------
#
# Script for installing a new version of a CDR publishing control document.
#
# Example usage:
#   UpdatePubControlDoc.py -p Y -c OCECDR-99999 elmer vewy-secwet Primary.xml
#
#----------------------------------------------------------------------
import argparse
import cgi
import getpass
import os
import re
import cdr

def create_parser():
    """
    Create the object which collects the run-time arguments.
    """

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
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

        Sample comment:   249320d (OCECDR-4285): New mailer type""")
    parser.add_argument("filename")
    parser.add_argument("--publishable", "-p", action="store_true")
    parser.add_argument("--tier", "-t")
    parser.add_argument("--comment", "-c")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--session", "-s")
    group.add_argument("--user", "-u")
    return parser

def get_doc_id(path, tier):
    """
    Extract the document title from the filename and look up the CDR
    document ID which matches the title.
    """

    basename = os.path.basename(path)
    if not basename.lower().endswith(".xml"):
        raise Exception("unexpected filename pattern %r" % basename)
    title = basename[:-4]
    doctype = "PublishingSystem"
    query = "CdrCtl/Title = {}".format(title)
    result = cdr.search("guest", query, doctypes=[doctype], tier=tier)
    if not result:
        raise Exception(u"Control document %r not found" % title)
    if len(result) > 1:
        raise Exception(u"Ambiguous title %r" % title)
    return result[0].docId

def main():
    """
    Store the new version of the filter.  Processing steps:

      1. Parse the command-line options and arguments.
      2. Load the new version of the control document from the file system.
      3. Find the CDR ID which matches the control document title
      4. Log into the CDR on the target server.
      5. Check out the document from the target CDR server.
      6. Store the new version on the target CDR server.
      7. Report the number of the new version.
      8. Clean up.
    """

    #------------------------------------------------------------------
    # 1. Parse the command-line options and arguments.
    #------------------------------------------------------------------
    parser = create_parser()
    opts = parser.parse_args()
    pub = "Y" if opts.publishable else "N"

    # If no comment is specified the last comment used (from the
    # all_docs table) would be stored.
    # Setting the comment to something to overwrite the last comment
    # -----------------------------------------------------------------
    comment = opts.comment or "Replaced w/o user comment"

    #------------------------------------------------------------------
    # 2. Load the new version of the control document from the file system.
    #------------------------------------------------------------------
    with open(opts.filename) as fp:
        xml = fp.read()
    if "]]>" in xml:
        parser.error("CdrDoc wrapper must be stripped from the file")

    #------------------------------------------------------------------
    # 3. Find out what the control document's document ID is.
    #------------------------------------------------------------------
    doc_id = get_doc_id(opts.filename, opts.tier)

    #------------------------------------------------------------------
    # 4. Log into the CDR on the target server.
    #------------------------------------------------------------------
    if opts.session:
        session = opts.session
    else:
        password = getpass.getpass()
        session = cdr.login(opts.user, password, tier=opts.tier)
        error_message = cdr.checkErr(session)
        if error_message:
            parser.error(error_message)

    #------------------------------------------------------------------
    # 5. Check out the document from the target CDR server.
    #------------------------------------------------------------------
    args = dict(checkout="Y", getObject=True, tier=opts.tier)
    doc = cdr.getDoc(session, doc_id, **args)
    error_message = cdr.checkErr(doc)
    if error_message:
        parser.error(error_message)

    #------------------------------------------------------------------
    # 6. Store the new version on the target CDR server.
    #------------------------------------------------------------------
    doc.xml = xml
    args = dict(
        doc=str(doc),
        checkIn="Y",
        reason=comment,
        comment=comment,
        ver="Y",
        val="Y",
        verPublishable=pub,
        tier=opts.tier,
        showWarnings=True
    )
    doc_id, warnings = cdr.repDoc(session, **args)
    if warnings:
        print(doc_id and "WARNINGS" or "ERRORS")
        for error in cdr.getErrors(warnings, asSequence=True):
            print(" -->", error)
    if not doc_id:
        print("aborting with failure")

    #------------------------------------------------------------------
    # 7. Report the number of the latest version.
    #------------------------------------------------------------------
    versions = cdr.lastVersions(session, doc_id, tier=opts.tier)
    print("Saved {} as version {}".format(doc_id, versions[0]))

    #------------------------------------------------------------------
    # 8. Clean up.
    #------------------------------------------------------------------
    if not opts.session:
        cdr.logout(session, tier=opts.tier)

if __name__ == "__main__":
    main()
