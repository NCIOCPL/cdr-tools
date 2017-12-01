#!/usr/bin/env python
#----------------------------------------------------------------------
#
# Script for installing a new version of an XSL/T filter in the CDR.
#
# JIRA::OCECDR-3694
#
#----------------------------------------------------------------------
import argparse
import cgi
import getpass
import re
import cdr

def create_parser():
    """
    Create the object which collects the run-time arguments.
    """

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""\
This program stores a new version of a filter on the CDR server.

The new version of the filter is obtained by reading the file named on
the command line, and the name of the file is expected to be in the format
"CDR9999999999.xml" where 9999999999 is the CDR ID of the filter as stored
on the production server.

It is recommended to provide the short git commit hash of the filter in
the comment option as well as the JIRA ticket number, particularly when
storing a new version of the filter on the production server.

    Sample comment:   e01f73e (OCECDR-4122): Re-order DrugInfo sections

SEE ALSO
  `CreateNewFilter.py` (add new filter stub document to the production tier)
  `InstallFilter.py` (adding new filter to another tier)
  `ModifyFilterTitle.py` (changing filter title)""")
    parser.add_argument("filename")
    parser.add_argument("--publishable", "-p", action="store_true")
    parser.add_argument("--tier", "-t", default=cdr.DEFAULT_HOST)
    parser.add_argument("--comment", "-c")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--session", "-s")
    group.add_argument("--user", "-u")
    return parser

def get_doc_id(xml, tier):
    """
    Extract the filter title from the document, and look up the CDR
    document ID which matches the title.
    """

    match = re.search("<!--\\s*filter title:(.*?)-->", xml, re.I)
    if not match:
        raise Exception("Filter title comment not found")
    title = match.group(1).strip()
    if not title:
        raise Exception("Filter title in document comment is empty")
    query = "CdrCtl/Title = {}".format(title)
    result = cdr.search("guest", query, doctypes=["Filter"], tier=tier)
    if not result:
        raise Exception(u"Filter %r not found" % title)
    if len(result) > 1:
        raise Exception(u"Ambiguous filter title %r" % title)
    return result[0].docId

def main():
    """
    Store the new version of the filter.  Processing steps:

      1. Parse the command-line options and arguments.
      2. Load the new version of the filter from the file system.
      3. Find the CDR ID which matches the filter title
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
    # 2. Load the new version of the filter from the file system.
    #------------------------------------------------------------------
    with open(opts.filename) as fp:
        xml = fp.read()
    if "]]>" in xml:
        parser.error("CdrDoc wrapper must be stripped from the file")

    #------------------------------------------------------------------
    # 3. Find out what the filter's document ID is.
    #------------------------------------------------------------------
    doc_id = get_doc_id(xml, opts.tier)

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
        setLinks="N",
        reason=comment,
        comment=comment,
        ver="Y",
        verPublishable=pub,
        tier=opts.tier
    )
    doc_id = cdr.repDoc(session, **args)
    error_message = cdr.checkErr(doc_id)
    if error_message:
        parser.error(error_message)

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
