#!/usr/bin/env python3
"""
Install a new filter on a lower-tier server

Script for installing a filter on a development or test server that
has already been created on the production server but has not yet
appeared on the server on which it will be installed now.

The program will add the filter as a new document, with a new ID, using
the title stored in the document on disk and in the production database.
"""

import argparse
import getpass
import re
import cdr
from cdrapi import db
from lxml import etree


def create_parser():
    """
    Create an option parser and associated usage, help, etc.
    """

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""\
Install a filter on a test or development server for the first time.
Filter must already have been created on the production server.
Filter will be installed on the requested server using the existing
name/title from production, and (almost certainly) a new CDR ID.

SEE ALSO
  `CreateNewFilter.py` (get a stable CDR ID on production for a new filter)
  `UpdateFilter.py` (modifying existing filter on any tier)
  `ModifyFilterTitle.py` (changing filter title)""")
    parser.add_argument("filename")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--session")
    group.add_argument("--user")
    parser.add_argument("--tier")
    return parser


class DocInfo:
    """
    Hold information parsed from the filter file on disk.
    """

    EXPECTED_ROOT = "{http://www.w3.org/1999/XSL/Transform}transform"

    def __init__(self, filename, parser):
        """
        Load filter from disk and locate relevant parts

        Pass:
            filename - name of file on disk containing XML for filter
            parser - used for reporting errors
        """

        # Initial values.
        self.xml = self.title = None

        # Parse filename to verify format.
        if not re.match("^CDR\\d{10}.xml$", filename):
            parser.error("File name must be in the form CDRnnnnnnnnnn.xml")

        # Load file
        try:
            # Translate line ends if needed to plain linefeed.
            with open(filename, "rb") as fp:
                self.xml = fp.read().replace(b"\r", b"")
        except Exception as e:
            parser.error("{}: {}".format(filename, e))

        # Parse.  Since we're creating the filters from our own
        # templates, we expect transform as the root element,
        # not stylesheet (which is also valid in the wild).
        try:
            root = etree.fromstring(self.xml)
            if root.tag != self.EXPECTED_ROOT:
                parser.error("{} is not a CDR XSL/T filter".format(filename))
        except SyntaxError as e:
            parser.error("Error parsing {}:\n{}".format(filename, e))

        # Extract the filter title.
        xml = self.xml.decode("utf-8")
        match = re.search(u"<!--\\s*filter title:(.*?)-->", xml, re.I)
        if not match:
            parser.error("{}: filter title comment not found".format(filename))
        self.title = match.group(1).strip()
        if not self.title:
            parser.error("{}: filter title comment is empty".format(filename))

    def check_unique_title(self, tier, parser):
        """
        Look for the title in the target server

        Make sure the document is not already installed in the target
        server.  This check is actually redundant, as the CDR server
        will enforce the assumption.  Can't hurt to check twice, though.

        Pass:
          tier - location of target server (if not localhost)
            parser - used for reporting errors

        Raise:
          exception if filter is already install on specified tier
        """

        cursor = db.connect(name="CdrGuest", tier=tier).cursor()
        query = db.Query("document d", "d.id")
        query.join("doc_type t", "t.id = d.doc_type")
        query.where(query.Condition("d.title", self.title))
        query.where("t.name = 'Filter'")
        rows = query.execute(cursor).fetchall()
        cursor.close()
        if rows:
            ids = ", ".join([str(row[0]) for row in rows])
            args = self.title, ids
            parser.error("{!r} already present ({}) in the CDR".format(*args))


def main():
    """
    Top-level entry point
    """

    # Process the command-line arguments.
    parser = create_parser()
    opts = parser.parse_args()

    # Make sure we're not doing this on the production server.
    if not opts.tier and cdr.isProdHost() or opts.tier == "PROD":
        parser.error("""
This program can only be used to install a filter on the development or
  test server, not production.
Use CreateFilter.py to create the filter in the production database, then
  use InstallFilter.py to install it in test or development with the same
  title/name and (almost certainly) a different local CDR ID.
""")

    # If we don't already have a session ID, make one.
    if not opts.session:
        password = getpass.getpass()
        session = cdr.login(opts.user, password, tier=opts.tier)
        error = cdr.checkErr(session)
        if error:
            parser.error(error)
    else:
        session = opts.session

    # Load the document.
    info = DocInfo(opts.filename, parser)

    # Make sure the filter isn't already installed
    info.check_unique_title(opts.tier, parser)

    # All checks passed: add the document.
    ctrl = dict(DocTitle=info.title.encode("utf-8"))
    doc = cdr.Doc(info.xml, doctype="Filter", ctrl=ctrl, encoding="utf-8")
    comment = "New filter install"
    add_opts = dict(doc=str(doc), comment=comment, tier=opts.tier)
    cdr_id = cdr.addDoc(session, **add_opts)
    error = cdr.checkErr(cdr_id)
    if error:
        parser.error(error)

    # Unlock the document and display its ID.
    try:
        cdr.unlock(session, cdr_id, tier=opts.tier)
        print(cdr_id)
    except Exception as e:
        parser.error(str(e))


if __name__ == "__main__":
    main()
