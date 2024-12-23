#!/usr/bin/env python3
"""Back out links to EVS concepts from CDR Term documents.

One of the CDR Admin regression tests finds CDR Term documents whose names
match those of an EVS concept but which have no link to any concept in the
EVS, and creates a new version of one of those term documents creating such
a link. There is a limited number of such documents (60 or so on CDR DEV as
of this writing), so there's a risk that a run of the tests might not find
any documents to link. This tool finds documents modified by such tests and
backs out the links to EVS conceps by applying the previous version (without
the concept link) as a new version.

You need to provide a host name for the CDR server, a valid session name
for that tier's server, the user ID for the account which ran the tests.
You can also optionally override the earliest date for which the script
will look for tests which linked the Term documents (default is December 2023)
and you can limit the number of documents which will be reverted (for testing
this script). You can include the --verbose flag to get the program to tell
you what it's doing (otherwise it's silent unless there are errors)

$ ./roll-back-evs-concept-links.py --help
usage: roll-back-evs-concept-links.py [-h] --host HOST --session SESSION
                                      --uid UID [--limit LIMIT]
                                      [--cutoff CUTOFF] [--verbose]

options:
  -h, --help         show this help message and exit
  --host HOST
  --session SESSION
  --uid UID
  --limit LIMIT
  --cutoff CUTOFF
  --verbose, -v
"""

from argparse import ArgumentParser
from datetime import datetime
from functools import cached_property
from pathlib import Path
from json import loads as load_from_json
from logging import getLogger, Formatter, FileHandler
from ssl import _create_unverified_context
from urllib.parse import urlencode
from urllib.request import urlopen


class Control:
    """Top-level logic for the script."""

    LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
    LOG_PATH = "test-cdr-admin.log"
    REFRESHED_COMMENT = "Term document refreshed from EVS"
    NOT_PRODUCTION = "Under no circumstances should this run in production!"
    LOGGER = getLogger("cdr-test")
    HANDLER = FileHandler(LOG_PATH, encoding="utf-8")
    HANDLER.setFormatter(Formatter(LOG_FORMAT))
    LOGGER.setLevel("INFO")
    LOGGER.addHandler(HANDLER)
    del HANDLER, LOG_FORMAT, LOG_PATH

    def run(self):
        """Top-level entry point."""

        start = datetime.now()
        if self.verbose:
            print(f"Checking {len(self.refreshed)} Term documents.")
            print(f"{len(self.eligible)} are eligible for unlinking.")
        done = 0
        for doc in self.eligible:
            if self.limit and done >= self.limit:
                break
            doc.unlink()
            if self.verbose:
                print(f"CDR{doc.id} unlinked.")
            done += 1
        if self.verbose:
            elapsed = datetime.now() - start
            print(f"elapsed: {elapsed}")

    def fetch(self, url):
        """Submit an HTTP request and return the bytes of the response.

        Required positional argument:
          url - string for the request (possibly wrapped in a Request object)

        Return:
          bytes returned from the HTTP server
        """

        try:
            context = _create_unverified_context()
            with urlopen(url, context=context) as response:
                return response.read()
        except Exception:
            self.logger.exception("failure fetching from %s", url)
            raise Exception(f"Unable to fetch {url}")

    def run_query(self, sql):
        """Execute a SQL query and return the results.

        Required positional argument:
          sql - string for the query to execute

        Return:
          2-dimensional array of row/column values
        """

        params = dict(sql=sql, Request="JSON")
        url = f"{self.cgi}/CdrQueries.py?{urlencode(params)}"
        json = self.fetch(url)
        try:
            return load_from_json(json)["rows"]
        except Exception:
            self.logger.exception("Failure running query")
            Path("results.json").write_bytes(json)

    @cached_property
    def base(self):
        """Root URL for the site."""
        return f"https://{self.host}"

    @cached_property
    def cgi(self):
        """Path to the CGI scripts."""
        return f"{self.base}/cgi-bin/cdr"

    @cached_property
    def cutoff(self):
        """Earliest date for the tests."""
        return self.opts.cutoff

    @cached_property
    def eligible(self):
        """Terms which are eligible for unlinking."""
        return [doc for doc in self.refreshed if doc.eligible]

    @cached_property
    def host(self):
        """The DNS name for the instance of IIS serving up the pages."""

        host = self.opts.host
        if host.lower() == "cdr.cancer.gov":
            raise Exception(self.NOT_PRODUCTION)
        return host

    @cached_property
    def limit(self):
        """Optional throttle for how many docs to revert."""
        return self.opts.limit

    @cached_property
    def logger(self):
        """Keep a record of what we do."""
        return self.LOGGER

    @cached_property
    def opts(self):
        """Run-time options collected from the command line."""

        parser = ArgumentParser()
        parser.add_argument("--host", required=True)
        parser.add_argument("--session", required=True)
        parser.add_argument("--uid", required=True, type=int)
        parser.add_argument("--limit", type=int, default=15)
        parser.add_argument("--cutoff", default="2023-12-01")
        parser.add_argument("--verbose", "-v", action="store_true")
        return parser.parse_args()

    @cached_property
    def refreshed(self):
        """Documents which were refresh by the testing user."""

        sql = (
            "SELECT DISTINCT id FROM doc_version "
            f"WHERE comment LIKE '{self.REFRESHED_COMMENT}%' "
            f"AND dt >= '{self.cutoff}' AND usr = {self.uid}"
        )
        ids = [int(row[0]) for row in self.run_query(sql)]
        return [self.Term(self, id) for id in ids]

    @cached_property
    def session(self):
        """String for the CDR login session's ID."""
        return self.opts.session

    @cached_property
    def uid(self):
        """Only back out the versions created by the user running the tests."""
        return self.opts.uid

    @cached_property
    def verbose(self):
        """Send more information to the console."""
        return self.opts.verbose

    class Term:
        """CDR Term document."""

        ROLLED_BACK = "Rolled back so it can be used by automated tests again."

        def __init__(self, control, id: int):
            """Capture the caller's values.

            Required positional arguments:
              control - support for database queries
              id - integer for the unique document ID
            """

            self.control = control
            self.id = id

        def __str__(self):
            """Display version of the document for listings."""

            versions = self.last_version, self.penultimate_version
            versions = [version.number for version in versions]
            versions = f"V{versions[0]:d} will be replaced by {versions[1]:d}"
            return f"CDR{self.id} {self.title} ({versions})"

        def unlink(self):
            """Restore an older version with the link to the EVS."""

            params = [
                ("id", str(self.id)),
                ("version", str(self.penultimate_version.number)),
                ("comment", self.ROLLED_BACK),
                ("Session", self.control.session),
                ("Request", "Confirm"),
                ("opts", "create-version"),
                ("opts", "pub-version"),
            ]
            script = "ReplaceCWDwithVersion.py"
            url = f"{self.control.cgi}/{script}?{urlencode(params)}"
            response = self.control.fetch(url)
            expected = f"Successfully updated CDR{self.id}."
            if expected.encode("ascii") not in response:
                Path("response.html").write_bytes(response)
                raise Exception("Version switch failed. Response saved.")

        @cached_property
        def eligible(self):
            """Is this document eligible for unlinking from the EVS concept?"""

            if self.last_version.uid != self.control.uid:
                return False
            comment = self.last_version.comment
            if not comment:
                return False
            if not comment.startswith(self.control.REFRESHED_COMMENT):
                return False
            if not self.last_version.linked:
                return False
            if self.penultimate_version is None:
                return False
            return False if self.penultimate_version.linked else True

        @cached_property
        def last_two_versions(self):
            """The two most recent versions created for this Term document."""

            sql = (
                "SELECT TOP 2 num, usr, title, xml, comment FROM doc_version "
                f"WHERE id = {self.id} ORDER BY num DESC"
            )
            return [self.Version(row) for row in self.control.run_query(sql)]

        @cached_property
        def last_version(self):
            """The final version created for this document."""
            return self.last_two_versions[0]

        @cached_property
        def penultimate_version(self):
            """The next-to-last version of the document, if any."""

            if len(self.last_two_versions) == 2:
                return self.last_two_versions[1]
            return None

        @cached_property
        def title(self):
            """Title of the CDR Term document."""
            return self.last_version.title.split(";")[0]

        class Version:
            """Information about a specific version of the document"""

            def __init__(self, values):
                """Capture the information about the version.

                Required positional argument:
                  values - values from the database query for the versions
                """

                self.number = int(values[0])
                self.uid = int(values[1])
                self.title = values[2].strip()
                self.linked = "</NCIThesaurusConcept>" in values[3]
                self.comment = values[4].strip()


if __name__ == "__main__":
    Control().run()