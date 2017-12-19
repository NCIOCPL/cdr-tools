#!/usr/bin/env python

"""
Deploy a fresh set of CDR schema or filter documents.

Used as part of a CDR release deployment, typically following an
invocation of `deploy-cdr.py`. This script is separated out from
that one because `install-docset.py` needs to import things that
`deploy-cdr.py` will probably need to install. That would work on
*nix, but Windows doesn't always play nice with file locking. We
could work around that problem with deferred local imports, but
it's cleaner to separate out this task to a separate script.

JIRA::OCECDR-4300
"""

import argparse
import logging
import os
import re
import subprocess
import sys
import cdr
#import cdrdb
import cdrapi.db as cdrdb

class DocumentSet:
    """
    Base class for master driver with runtime configuration settings.

    Class values:
      POPEN_OPTS - options for launching a sub process

    Attributes:
      logger - object for recording what we do
      opts - runtime control settings
      session - authority to add/update documents being installed
      cursor - for running guest CDR database queries
    """

    POPEN_OPTS = dict(
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )

    def __init__(self, opts):
        """
        Collect and validate runtime settings and set up logging.
        """

        self.logger = cdr.Logging.get_logger("deploy", console=True)
        self.opts = opts
        self.session = self.login()
        self.cursor = cdrdb.connect(name="CdrGuest").cursor()

    def login(self):
        """
        Create a CDR login session for adding/updating the documents.
        """

        if self.opts.test:
            return None
        password = cdr.getpw(self.ACCOUNT)
        if not password:
            self.logger.error("account password not found")
            sys.exit(1)
        session = cdr.login(self.ACCOUNT, password)
        error = cdr.checkErr(session)
        if error:
            self.logger.error(error)
            sys.exit(1)
        return session

    def run(self):
        """
        Install the documents and perform any necessary postprocessing.
        """

        if not os.path.isdir(opts.source):
            self.logger.error("%s not found", opts.source)
            sys.exit(1)
        action = "comparing" if opts.test else "installing"
        doctype = self.DOCTYPE.lower()
        self.logger.info("%s %ss", action, doctype)
        self.logger.info("from %s", opts.source)
        changes = 0
        for name in os.listdir(self.opts.source):
            if name.endswith(".xml"):
                xml = open(os.path.join(self.opts.source, name), "rb").read()
                doc = self.Document(self, name, xml)
                if doc.install():
                    changes += 1
        if changes:
            if not self.opts.test:
                self.post_process()
        else:
            self.logger.info("%ss already up to date", doctype)
        if not self.opts.test:
            cdr.logout(self.session)
            self.logger.info("%s installation complete", doctype)

    def post_process(self):
        """
        Override in the derived class as appropriate.
        """

    @staticmethod
    def fetch_options():
        """
        Parse and validate the command-line arguments.
        """

        desc = "Install a fresh set of CDR filters or schemas"
        doctypes = "schema", "filter"
        parser = argparse.ArgumentParser(description=desc)
        parser.add_argument("source", help="path location of document set")
        parser.add_argument("doctype", choices=doctypes)
        parser.add_argument("--test", "-t", action="store_true",
                            help="don't store, just compare and report")
        opts = parser.parse_args()
        return opts

    @classmethod
    def execute(cls, args):
        """
        Run an external program and return the results.
        """

        p = subprocess.Popen(args, **cls.POPEN_OPTS)
        output, error = p.communicate()
        class Result:
            def __init__(self, code, output):
                self.code = code
                self.output = output
        return Result(p.returncode, output)

    class Document:
        """
        A CDR document to be installed if new or changed.
        """

        def __init__(self, control, name, xml):
            """
            Store the properties not dependent on document type.
            """

            self.name = self.title = name
            self.xml = xml
            self.control = control
            self.doctype = control.DOCTYPE
            self.id = self.old = None

        def fetch_doc(self):
            """
            Retrieve the document ID and stored XML if not new.
            """

            query = cdrdb.Query("document d", "d.id", "d.xml")
            query.join("doc_type t", "t.id = d.doc_type")
            query.where(query.Condition("t.name", self.doctype))
            query.where(query.Condition("d.title", self.title))
            rows = query.execute(self.control.cursor).fetchall()
            if not rows:
                return
            if len(rows) > 1:
                self.logger.warning("multiple %r docs", self.title)
            else:
                self.id, self.old = rows[0]
            path = "D:/tmp/existing-filters/CDR{:010d}.xml".format(self.id)
            with open(path, "wb") as fp:
                fp.write(self.old.encode("utf-8"))
                print(path)
                

        def install(self):
            """
            Install CDR document if it is new or changed.

            Return False if document unchanged; otherwise True
            """

            if not self.id:
                return self.add()
            elif self.changed():
                return self.replace()
            return False

        def changed(self):
            """
            Compare the old and new docs.

            Ignore leading and trailing whitespace differences.
            """

            old = self.old.strip().replace("\\r", "").encode("utf-8")
            return self.xml.strip() != old

        def add(self):
            """
            Add the document to the CDR repository (if not testing).

            Return True, which is bubbled up to the main loop in `run()`.
            """

            if self.control.opts.test:
                self.control.logger.info("%s is new", self.name)
                return True
            comment = "Added by install-docset.py"
            ctrl = { "DocTitle": self.title }
            opts = { "type": self.doctype, "encoding": "utf-8", "ctrl": ctrl }
            cdr_doc = cdr.Doc(self.xml, **opts)
            opts = dict(doc=str(cdr_doc), checkIn="Y", ver="Y", comment=comment)
            cdr_id = cdr.addDoc(self.control.session, **opts)
            error = cdr.checkErr(cdr_id)
            if error:
                self.control.logger.error(error)
                sys.exit(1)
            self.control.logger.info("added %s as %s", self.name, cdr_id)
            return True

        def replace(self):
            """
            Update an existing CDR document (if not testing).

            Return True, which is bubbled up to the main loop in `run()`.
            """

            if self.control.opts.test:
                self.control.logger.info("%s is changed", self.name)
                return True
            cdr.checkOutDoc(self.control.session, self.id, force="Y")
            comment = "Updated by install-docset.py"
            ctrl = { "DocTitle": self.title }
            opts = { "type": self.doctype, "encoding": "utf-8", "ctrl": ctrl }
            opts["id"] = cdr.normalize(self.id)
            cdr_doc = cdr.Doc(self.xml, **opts)
            opts = dict(doc=str(cdr_doc), checkIn="Y", ver="Y", comment=comment)
            cdr_id = cdr.repDoc(self.control.session, **opts)
            error = cdr.checkErr(cdr_id)
            if error:
                self.control.logger.error(error)
                sys.exit(1)
            self.control.logger.info("replaced %s (%s)", self.name, cdr_id)
            return True

class SchemaSet(DocumentSet):
    """
    Processing control for installing a CDR schema document set.

    The custom part for schemas is the postprocessing.

    Class values:
      CHECK_DTDS - path to script to rebuild the client DTD files
      REFRESH_MANIFEST - path to script to rebuild the client manifest
      ACCOUNT - name of CDR account for installing schemas
    """

    CHECK_DTDS = cdr.WORK_DRIVE + r":\cdr\Build\CheckDtds.py"
    REFRESH_MANIFEST = cdr.WORK_DRIVE + r":\cdr\Build\RefreshManifest.py"
    ACCOUNT = "SchemaUpdater"
    DOCTYPE = "schema"

    def post_process(self):
        """
        Rebuild fresh DTDs and the client manifest.
        """

        self.rebuild_dtds()
        self.refresh_manifest()

    def rebuild_dtds(self):
        """
        Reflect changes to the schemas in regenerated DTDs for XMetaL.
        """

        args = "python", self.CHECK_DTDS
        result = self.execute(args)
        if result.code:
            self.logger.error("failure rebuilding DTDs: %s", result.output)
            sys.exit(1)
        self.logger.info("rebuild client dtds")

    def refresh_manifest(self):
        """
        Make sure the client manifest refrects changes to the DTDs
        """

        args = "python", self.REFRESH_MANIFEST
        result = self.execute(args)
        if result.code:
            self.logger.error("failure refreshing manifest: %s", result.output)
            sys.exit(1)
        self.logger.info("refreshed client manifest")

    class Document(DocumentSet.Document):
        """
        A CDR schema document to be installed if new or changed.

        """

        def __init__(self, control, name, xml):
            """
            Store the properties, encoding the xml using utf-8.
            """

            DocumentSet.Document.__init__(self, control, name, xml)
            self.fetch_doc()

class FilterSet(DocumentSet):
    """
    Processing control for installing a CDR filter document set.

    The tricky bit for filters is finding the document title.

    Class values:
      ACCOUNT - name of CDR account for installing filters
      DOCTYPE - CDR name for document type
    """

    DOCTYPE = "Filter"
    ACCOUNT = "ReleaseInstaller"

    class Document(DocumentSet.Document):
        """
        A CDR filter document to be installed if new or changed.
        """

        def __init__(self, control, name, xml):
            """
            Store the properties, encoding the xml using utf-8.
            """

            DocumentSet.Document.__init__(self, control, name, xml)
            match = re.search("<!--\\s*filter title:(.*?)-->", xml, re.I)
            if not match:
                self.control.logger.warning("title not found in %s", name)
                self.title = ""
            else:
                self.title = match.group(1).strip()
                if not self.title:
                    self.control.logger.warning("empty title for %s", name)
                else:
                    self.fetch_doc()

if __name__ == "__main__":
    "Top-level entry point."

    opts = DocumentSet.fetch_options()
    dict(schema=SchemaSet, filter=FilterSet)[opts.doctype](opts).run()
