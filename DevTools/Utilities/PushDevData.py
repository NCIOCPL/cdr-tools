#!/usr/bin/env python

"""
Restore development work following a refresh from PROD

Replaces copies of CDR control documents which have been preserved
from the development server, after a refresh of the database on
the development server from the production server.  This allows us
to work with the users' current production documents without losing
work done by developers on the development server.
"""

# Standard libraries
from argparse import ArgumentParser

# Local project libraries
import cdr
from cdrapi import db
from cdrapi.settings import Tier
import cdr_dev_data


def main():
    """
    Top-level program logic.

    1. Initialization
    2. Restore control documents
    3. Restore new document types (with their documents)
    4. Release resources
    """

    # 1. Initialization
    job = Job()

    # 2. Restore control tables (not implemented)
    #    Although the content of the control DB tables is extracted as
    #    part of the PullDevDocs process it was not part of the original
    #    implementation to restore.
    #    Due to the complexity of restoring multiple complete tables,
    #    think permissions, DB foreign keys, etc. a decision was made to
    #    continue with the current restore process and exclude DB tables.
    # job.restore_tables()

    # 3. Restore old document types
    job.restore_old_doctypes()

    # 4. Restore new document types
    job.restore_new_doctypes()

    # 5. Clean up after ourselves.
    job.clean_up()


class Job:
    """
    Object which performs the work of restoring CDR documents on DEV.
    """

    DEVELOPERS = "Developers"
    COMMENT = "preserving work on development server"
    CONTENTTYPES = (
        'DrugInformationSummary',
        'GlossaryTermConcept',
        'GlossaryTermName',
        'Media',
        'Summary',
        'Term'
    )
    ACTIONS = (
        'ADD DOCUMENT',
        'DELETE DOCTYPE',
        'DELETE DOCUMENT',
        'FILTER DOCUMENT',
        'FORCE CHECKIN',
        'FORCE CHECKOUT',
        'GET DOCTYPE',
        'GET SCHEMA',
        'MODIFY DOCTYPE',
        'MODIFY DOCUMENT',
        'PUBLISH DOCUMENT',
        'VALIDATE DOCUMENT',
    )

    def __init__(self):
        """
        Constructs job control object for restoring data on CDR DEV server.

        1. Make sure we're running on the DEV tier.
        2. Get the parameters for this job.
        3. Create the control object for the job.
        """

        # 1. Safety check.
        if Tier().name not in ["DEV", "QA"]:
            raise Exception("This script must only be run on the DEV or QA tier.")

        # 2. Get what we need from the command line.
        parser = ArgumentParser()
        parser.add_argument("--directory", required=True,
                            help="directory to restore from")
        parser.add_argument("--user", required=True,
                            help="user ID")
        parser.add_argument("--session", required=True,
                            help="user session")
        parser.add_argument("--skip-content", action="store_true",
                            help="exclude practice documents "
                            "from being restored")
        opts = parser.parse_args()

        # 3. Create objects used to do the job's work.
        self._logger = cdr.Logging.get_logger("PushDevData", console=True)
        self._conn = db.connect(user="CdrGuest")
        self._cursor = self._conn.cursor()
        self._dir = opts.directory
        self._skip_content = opts.skip_content or False
        self._old = cdr_dev_data.Data(self._dir)
        self._new = cdr_dev_data.Data(self._cursor, self._old)
        self._uid = opts.user
        self._session = opts.session
        self._logger.info("session %s", self._session)
        self._logger.info("using data preserved in %s", self._dir)
        self._new_doc_types = []

    def restore_old_doctypes(self):
        """
        Restores the documents for document types which already exist.

        Documents which are new are created.  Documents which are found
        in the repository (by unique document title) are modified with
        a new version.
        """

        # Walk through the preserved documents by type.
        msg = "restoring docs for control doctypes and test content"
        if self._skip_content:
            msg = "restoring docs for control doctypes only"

        self._logger.info(msg)

        for doc_type in sorted(self._old.docs):
            # 'Old' docs were on DEV before refresh; 'new' are post refresh.
            old = self._old.docs[doc_type].docs
            new = self._new.docs[doc_type].docs

            if new:
                if self._skip_content and doc_type in Job.CONTENTTYPES:
                    self._logger.info("skipping %r docs", doc_type)
                    continue
                else:
                    self._logger.info("restoring %r docs", doc_type)

                # Documents are keyed by unique title.
                for key in old:
                    old_id, old_title, old_xml = old[key]

                    # If PROD didn't have the document, (re-)create it.
                    if key not in new:
                        self._logger.info(f"Adding new document '{old_title}'")
                        self._add_doc(doc_type, old_title, old_xml)
                    else:

                        # PROD had it; if it differs, restore what was on DEV.
                        new_id, new_title, new_xml = new[key]
                        if self._differ(old_xml, new_xml):
                            self._mod_doc(doc_type, old_title, old_xml, new_id)
            else:

                # Defer documents for types we have to re-create
                self._logger.info("deferring %r docs", doc_type)
                self._new_doc_types.append(doc_type)

    def restore_new_doctypes(self):
        """
        Re-create documents whose doctype was not in the PROD repository.

        First re-create the document type, then add each of the documents
        for that document type which had been on DEV.
        """
        self._logger.info("restoring new document types")
        for doc_type in self._new_doc_types:
            if self._create_doctype(doc_type):
                docs = self._old.docs[doc_type].docs
                for key in docs:
                    doc_id, doc_title, doc_xml = docs[key]
                    self._add_doc(doc_type, doc_title, doc_xml)

    def clean_up(self):
        """
        Don't leave an open CDR session hanging around.
        """
        # The user and session ID are mandatory command line parameters
        # Don't need to close the session.
        # cdr.logout(self._session)

        self._logger.info("restoration complete")

    def _create_doctype(self, name):
        """
        Create a document type which had been on DEV but not on PROD.

        1. Extract the information about the doctype from the saved table.
        2. Plug in the doctype's title filter, if any.
        3. Add permissions for developers to work with docs of this type.

        2021-12-31: suppress pylint false positives
        """

        # The preserved doc_type table and filter and schema docs have
        # the information we need.
        self._logger.info("creating %r doctype", name)
        table = self._old.tables["doc_type"]
        row = table.names[name]
        filter_id = self._get_filter_id(row["title_filter"])
        comment = row["comment"]
        schema_id = row["xml_schema"]
        schema = self._old.docs["Schema"].map[schema_id]
        opts = {"type": name, "format": "xml", "versioning": "Y",
                "schema": schema, "comment": comment}
        info = cdr.dtinfo(**opts)
        info = cdr.addDoctype(self._session, info)
        if info.error:  # pylint: disable=no-member
            args = name, info.error  # pylint: disable=no-member
            self._logger.error("unable to create doctype %r: %s", *args)
            return False

        # Plug in the document type's title filter, if any.
        if filter_id:
            self._cursor.execute("""\
                UPDATE doc_type
                   SET title_filter = ?
                 WHERE name = ?""", (filter_id, name))
            self._conn.commit()

        # Let developers work with the new document type on DEV.
        group = cdr.getGroup(self._session, Job.DEVELOPERS)
        for action in self.ACTIONS:
            group.actions[action].append(name)
        try:
            cdr.putGroup(self._session, Job.DEVELOPERS, group)
        except Exception:
            message = "unable to update permissions for doctype %r"
            self._logger.exception(message, name)
            raise

        # Report success.
        return True

    def _get_filter_id(self, old_id):
        """
        Look up the CDR ID for a document type's filter.

        We do this by finding the filter document's title, and then
        looking up the ID by this unique title.  This is necessary
        because the filter document may have disappeared and thus
        had to be re-created.
        """

        filter_title = self._old.docs["Filter"].map[old_id]
        self._cursor.execute("""\
            SELECT d.id
              FROM document d
              JOIN doc_type t
                ON t.id = d.doc_type
             WHERE t.name = 'Filter'
               AND d.title = ?""", filter_title)
        rows = self._cursor.fetchall()
        return rows and rows[0][0] or None

    def _add_doc(self, doc_type, doc_title, doc_xml):
        """
        Add a document which was lost because it was not on PROD.
        """

        self._logger.info("adding %r document %r", doc_type, doc_title)

        # Wrap the document XML in the CdrDoc wrapper and create it.
        doc = cdr.makeCdrDoc(doc_xml, doc_type, ctrl={"DocTitle": doc_title})
        doc_id = cdr.addDoc(self._session, doc=doc, checkIn="N",
                            comment=Job.COMMENT, reason=Job.COMMENT)
        err = cdr.checkErr(doc_id)
        if err:
            self._logger.error("failure creating document: %s", err)
            return

        # Newly created document need to be versioned and unlocked separately.
        doc = self._lock_doc(doc_id)
        if doc:
            response = cdr.repDoc(self._session, doc=str(doc), checkIn="Y",
                                  val="Y", ver="Y", reason=Job.COMMENT,
                                  comment=Job.COMMENT)
            err = cdr.checkErr(response)
            if err:
                self._logger.error("failure unlocking %s: %s", doc_id, err)

    def _mod_doc(self, doc_type, doc_title, doc_xml, doc_id):
        """
        Add a new version for a document which was different on the two tiers.
        """

        args = doc_type, doc_title, doc_id
        self._logger.info("updating %r document %r (CDR%d)", *args)

        # Lock the document, breaking any existing locks if necessary.
        doc = self._lock_doc(doc_id)
        if doc:

            # Plug in the preserved XML from PROD and create the new version.
            doc.xml = doc_xml.encode("utf-8")
            doc.ctrl["DocTitle"] = doc_title.encode("utf-8")
            response = cdr.repDoc(self._session, doc=str(doc), checkIn="Y",
                                  val="Y", ver="Y", reason=Job.COMMENT,
                                  comment=Job.COMMENT)
            err = cdr.checkErr(response)
            if err:
                args = cdr.normalize(doc_id), err
                self._logger.error("failure saving %s: %s", *args)

    def _lock_doc(self, doc_id):
        """
        Check out an existing CDR document.
        """

        # If someone else has the document locked, break the lock.
        locker = self._find_locker(doc_id)
        if locker and locker.lower() != self._uid.lower():
            if not self._unlock_doc(doc_id):
                return None

        # Fetch the document with a lock.
        doc = cdr.getDoc(self._session, doc_id, checkout="Y", getObject=True)
        err = cdr.checkErr(doc)
        if not err:
            return doc
        args = cdr.normalize(doc_id), err
        self._logger.error("failure locking %s: %r", *args)
        return None

    def _unlock_doc(self, doc_id):
        """
        Release an existing lock on a CDR document.
        """
        id_string = cdr.normalize(doc_id)
        try:
            cdr.unlock(self._session, id_string, comment=Job.COMMENT)
        except Exception as e:
            self._logger.error("failure unlocking %s: %s", id_string, e)
            return False
        return True

    def _differ(self, old, new):
        """
        Compare two versions of a CDR document.
        """
        return self._normalize(old) != self._normalize(new)

    def _normalize(self, xml):
        """
        Eliminate differences in line ending sequences for a document.
        """
        return xml.replace("\r", "")

    def _find_locker(self, id):
        """
        Find out who (if anyone) has a specified document checked out.
        """
        self._cursor.execute("""\
            SELECT u.name
              FROM usr u
              JOIN checkout c
                ON c.usr = u.id
             WHERE c.id = ?
               AND c.dt_in IS NULL
          ORDER BY dt_out DESC""", cdr.exNormalize(id)[1])
        rows = self._cursor.fetchall()
        return rows and rows[0][0] or None


# ----------------------------------------------------------------------
# Entry point.
# ----------------------------------------------------------------------
if __name__ == "__main__":
    main()
