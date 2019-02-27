"""
Example template for one-off global change jobs

Uses the lxml.etree parser to perform the document modifications.
Uses SQL to select documents to be processed.
Command-line option can be used to override document selection for testing.

If you encounter a global change request which requires unusual
techniques not represented in this example template, and which might
prove useful for subsequent jobs, consider enhancing this template to
incorporate what you learned when implementing the job, or (if that
isn't appropriate) adding another template, named appropriately to
reflect the condition it represents (to make it easy to find the
example when you need it).
"""

from argparse import ArgumentParser
from re import compile
from lxml import etree
from ModifyDocs import Job
from cdrapi import db


class OneOffGlobal(Job):
    """
    Derived class for a specific document transformation job
    """

    COMMENT = "Convert ExternalRef elements to ProtocolRef. OCECDR-4551"
    PATTERN = compile(r"NCT\d+")

    def __init__(self, **opts):
        """
        Capture control settings for job

        Invoke the base class constructor with the user's options,
        then determine the list of documents to be transformed.

        Typically, the actual determination as to which documents
        are to be processed will have been made by the time the
        constructor has completed. However, there would be no harm
        done if the work to make this determination were deferred
        until the `select()` method is invoked.

        Different types of global change jobs call for various
        techniques for selecting documents. For example, for some
        requests, the users will supply a spreadsheet file containing
        a column containing the CDR IDs of the documents to be
        transformed (and frequently other columns with information
        about specific values to be used in that transformation).

        Optional keyword arguments:
          session - string representing CDR login
          user - CDR user account name (exactly one of `sesssion` or `user`
                 must be provided)
          mode - "test" (the default) or "live"
          tier - "DEV" | "QA" | "STAGE" | "PROD"
          docs - sequence of document IDs, used to optionally override
                 (for testing) the documents which would be identified
                 by the SQL query below)
        """

        # Pull out the list of documents from the command line (if any).
        self.__doc_ids = opts.pop("docs")

        # Invoke the base class constructor with the user's options.
        Job.__init__(self, **opts)

        # If no documents were specified on the command line, use SQL.
        # Some things to note:
        #   - query_term_pub.path takes care of determining document type
        #   - the `Job` class comes with its own read-only cursor
        #   - when document IDs are specified on the command line, the
        #     order of specification is preserved, but when we use the
        #     database we're sorting by document ID (at least in this case).
        #     Typically, the order doesn't really matter, but it might in
        #     some cases. Do whatever you need to do for the requirements
        #     of the specific job you're working on.
        if not self.__doc_ids:
            query = db.Query("pub_proc_cg c", "c.id", "u.value")
            query.join("query_term_pub u", "u.doc_id = c.id")
            query.where("u.path LIKE '/Summary%ExternalRef/@cdr:xref'")
            query.where("u.value LIKE 'https://clinicaltrials.gov/%NCT%'")
            query.order("c.id")
            rows = query.execute(self.cursor).fetchall()
            self.__doc_ids = [row[0] for row in rows]

    def select(self):
        """
        Return the sequence of CDR document IDs for this job
        """

        return sorted(self.__doc_ids)

    def transform(self, doc):
        """
        Replace `ExternalRef` elements with `ProtocolRef` elements

        Logic:
          - find all `ExternalRef` elements within the document
          - if the `cdr:xref` element has an NCT ID:
            - Create a new `ProtocolRef` element with the information
              from the `ExternalRef` element
            - Replace the `ExternalRef` with the `ProtocolRef` element

        N.B.: `ExternalRef` is an inline element and may therefore
              include a `tail` which needs to be propagated to the
              replacing element.

        Pass:
          doc - reference to `cdr.Doc` object for document to be modified

        Return:
          serialized transformed document XML, encoded as UTF-8
        """

        root = etree.fromstring(doc.xml)
        for node in root.iter("ExternalRef"):
            url = node.get("{cips.nci.nih.gov/cdr}xref")
            match = self.PATTERN.search(url)
            if match:
                replacement = etree.Element("ProtocolRef")
                replacement.text = node.text
                replacement.tail = node.tail
                replacement.set("nct_id", match.group())
                replacement.set("comment", "Converted from ExternalRef")
                node.getparent().replace(node, replacement)
        return etree.tostring(root, encoding="utf-8")


if __name__ == "__main__":
    """
    Collect the command-line options, create the job, and run it
    """

    parser = ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--session", "-s")
    group.add_argument("--user", "-u")
    parser.add_argument("--mode", "-m", default="test")
    parser.add_argument("--tier", "-t")
    parser.add_argument("--docs", "-d", nargs="*", type=int)
    opts = parser.parse_args()
    job = OneOffGlobal(**vars(opts))
    job.run()
