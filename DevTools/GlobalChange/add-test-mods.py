#!/usr/bin/env python

"""Make a trivial change to force publishing to push the documents.
"""

from argparse import ArgumentParser
from datetime import datetime
from lxml import etree
from cdrapi import db
from ModifyDocs import Job

class TestMods(Job):
    """
    Derived class for a specific document transformation job
    """

    COMMENT = "Add trivial change to force publishing to push"
    LOGNAME = "add-test-mods"
    TESTING = " (TESTING-MOD-"
    STAMP = datetime.now().strftime("%Y%m%d%H%M%S")
    SUFFIX = f"{TESTING}{STAMP})"
    PATHS = dict(
        # DrugInformationSummary="DrugInfoMetaData/Description",
        DrugInformationSummary="Title",
        GlossaryTermName="TermName/TermNameString",
        Summary="SummaryMetaData/SummaryDescription",
        Media="MediaTitle",
        Organization="OrganizationNameInformation/OfficialName/Name",
        Person="PersonNameInformation/SurName",
        PoliticalSubUnit="PoliticalSubUnitFullName",
        Term="PreferredName",
    )

    def __init__(self, **opts):
        """Snag a copy of the options on the way to the base class.
        """

        self.__opts = opts
        Job.__init__(self, **opts)

    @property
    def count(self):
        """How many documents should we modify?"""

        if not hasattr(self, "_count"):
            self._count = self.__opts["count"]
        return self._count

    @property
    def doctype(self):
        """String for the name of the document type."""

        if not hasattr(self, "_doctype"):
            self._doctype = self.__opts["doctype"]
        return self._doctype

    @property
    def element(self):
        """String for the path to the element from the root."""

        if not hasattr(self, "_element"):
            self._element = self.__opts.get("element")
            if not self._element:
                self._element = self.PATHS[self.doctype]
        return self._element

    @property
    def ids(self):
        """Sequence of CDR document IDs."""

        if not hasattr(self, "_ids"):
            self._ids = self.__opts.get("ids")
            if not self._ids:
                query = db.Query("document d", "d.id").limit(self.count)
                query.order("d.id")
                query.join("doc_type t", "t.id = d.doc_type")
                query.join("pub_proc_cg c", "c.id = d.id")
                query.where(query.Condition("t.name", self.doctype))
                rows = query.execute(self.cursor).fetchall()
                self._ids = sorted([row.id for row in rows])
        return self._ids

    def select(self):
        """Return the sequence of CDR document IDs for this job.
        """

        return self.ids

    def transform(self, doc):
        """Modify the specified element.

        Pass:
          doc - reference to `cdr.Doc` object for document to be modified

        Return:
          serialized transformed document XML, encoded as UTF-8
        """

        root = etree.fromstring(doc.xml)
        node = root.find(self.element)
        if node is None:
            raise Exception(f"{doc.id}: missing {self.element}")
        text = (node.text or "").split(self.TESTING)[0]
        node.text = f"{text}{self.SUFFIX}"
        return etree.tostring(root, encoding="utf-8")

if __name__ == "__main__":
    """
    Collect the command-line options, create the job, and run it
    """

    doctypes = sorted(TestMods.PATHS)
    parser = ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--session")
    group.add_argument("--user")
    parser.add_argument("--mode", default="test")
    parser.add_argument("--tier")
    parser.add_argument("--element")
    parser.add_argument("--ids", type=int, nargs="*", metavar="ID")
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--doctype", required=True, choices=doctypes)
    opts = parser.parse_args()
    job = TestMods(**vars(opts))
    job.run()
    print(" ".join([str(id) for id in job.ids]))

