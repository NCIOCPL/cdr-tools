"""
Example template for one-off global change jobs

Uses the lxml.etree parser to perform the document modifications.
"""

from argparse import ArgumentParser
from lxml import etree
from ModifyDocs import Job


class OneOffGlobal(Job):
    """
    Derived class for a specific document transformation job
    """

    COMMENT = "Add bar children to all foos (JIRA::OCECDR-12345)"

    def __init__(self, doc_ids, **opts):
        """
        Capture control settings for job

        Invoke the base class constructor with the user's options,
        then remember the list of documents to be transformed.
        """

        Job.__init__(self, **opts)
        self.__doc_ids = doc_ids

    def select(self):
        """
        Return the sequence of CDR document IDs for this job
        """

        return self.__doc_ids

    def transform(self, doc):
        """
        Add a `bar` child to each `foo` node

        Pass:
          doc - reference to `cdr.Doc` object for document to be modified

        Return:
          serialized transformed document XML, encoded as UTF-8
        """

        root = etree.fromstring(doc.xml)
        for node in root.findall("foo"):
            etree.SubElement(node, "bar").text = u"foobar"
        return etree.tostring(root, encoding="utf-8")


if __name__ == "__main__":
    """
    Collect the command-line options, create the job, and run it
    """

    parser = ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--session")
    group.add_argument("--user")
    parser.add_argument("--mode", default="test")
    parser.add_argument("--tier")
    opts = parser.parse_args()
    docs = 444444, 555555, 666666
    job = OneOffGlobal(docs, **vars(opts))
    job.run()
