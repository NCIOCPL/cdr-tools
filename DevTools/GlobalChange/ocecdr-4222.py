#----------------------------------------------------------------------
# Update URLs redirected from http to https (OCECDR-4222).
#----------------------------------------------------------------------
import argparse
import datetime
import requests
import sys
import urlparse
import lxml.etree as etree
import cdr
import cdrdb2 as cdrdb
import ModifyDocs

class Control:
    """
    Exposes callback for global change harness.
    """

    logger = cdr.Logging.get_logger("ocecdr-4222")
    DOCTYPES = (
        "Citation",
        "ClinicalTrialSearchString",
        "DrugInformationSummary",
        "GlossaryTermConcept",
        "MiscellaneousDocument",
        "Summary",
    )
    NAMESPACE = "cips.nci.nih.gov/cdr"
    NAMESPACES = { "cdr": NAMESPACE }
    XREF = "{%s}xref" % NAMESPACE

    def __init__(self, cache):
        """
        Determine what needs to be changed, either from the database or a cache.
        """

        self.urls = {}
        if cache:
            self.ids = eval(cache.readline().strip())
            for line in cache:
                old, new = eval(line.strip())
                self.urls[old] = new
        else:
            self.find_links()
        self.logger.info("mapped %d redirected urls", len(self.urls))
        self.logger.info("queued %d documents for processing", len(self.ids))

    def getDocIds(self):
        """
        Callback invoked by the global change harness.
        """

        return sorted(self.ids)

    def run(self, docObject):
        """
        Callback invoked by the global change harness once for each document.

        Performs two separate tasks:
         1. strip out all the MobileURL elements
         2. update links with URLs redirected from http to https
        """

        root = etree.fromstring(docObject.xml)
        etree.strip_elements(root, "MobileURL")
        for node in root.xpath("//*[@cdr:xref]", namespaces=self.NAMESPACES):
            old_url = node.get(self.XREF)
            new_url = self.urls.get(old_url)
            if new_url:
                node.set(self.XREF, new_url)
                id = docObject.id
                self.logger.info("%s: mapped %s to %s", id, old_url, new_url)
        return etree.tostring(root)

    def find_links(self):
        """
        Test the external links to find out which are redirected or are
        in obsolete MobileURL elements.
        """

        fields = "x.doc_id", "x.path", "x.value"
        query = cdrdb.Query("query_term x", *fields)
        query.join("document d", "d.id = x.doc_id")
        query.join("doc_type t", "t.id = d.doc_type")
        query.where(query.Condition("t.name", self.DOCTYPES, "IN"))
        query.where("path LIKE '%/@cdr:xref'")
        query.where("value LIKE 'http://%'")
        links = query.execute().fetchall()
        opts = { "timeout": 5, "allow_redirects": False }
        self.ids = set()
        #dead_hosts = set()
        urls = {}
        done = redirects = 0
        for doc_id, path, url in links:
            if "MobileURL" in path:
                self.ids.add(doc_id)
            elif url in urls:
                if urls[url]:
                    self.ids.add(doc_id)
            else:
                urls[url] = None
                components = urlparse.urlparse(url)
                if True: #components.netloc not in dead_hosts:
                    try:
                        self.logger.info(url)
                        response = requests.get(url, **opts)
                        if response.status_code / 100 == 3:
                            try:
                                response = requests.get(url, timeout=5)
                                if response.status_code == 200:
                                    new_url = response.url
                                    if not new_url:
                                        message = "no new url for %r"
                                        self.logger.error(message, url)
                                    elif new_url.startswith("https://"):
                                        urls[url] = new_url
                                        self.ids.add(doc_id)
                                        redirects += 1
                            except Exception:
                                err = "following redirect for %r in CDR%d"
                                self.logger.exception(err, url, doc_id)
                    except Exception:
                        self.logger.exception("connecting to %r", url)
                        #dead_hosts.add(components.netloc)
            done += 1
            sys.stderr.write("\r%d redirects in %d of %d links" %
                             (redirects, done, len(links)))
        self.urls = {}
        stamp = cdr.make_timestamp()
        with open("ocecdr-4222-%s.cache" % stamp, "w") as cache:
            cache.write("%r\n" % self.ids)
            for url, redirect in urls.items():
                if redirect:
                    self.urls[url] = redirect
                    cache.write("%s\n" % repr((url, redirect)))
        sys.stderr.write("\ndone\n")

    @classmethod
    def main(cls):
        """
        Top-level entry point.

        Logic:
          1. collect options
          2. create object exposing callbacks
          3. create global change job
          4. run the job
        """

        start = datetime.datetime.now()
        parser = argparse.ArgumentParser(description="Replace redirected URLs")
        parser.add_argument("--user")
        parser.add_argument("--password", default="")
        parser.add_argument("--session")
        parser.add_argument("--cache", type=argparse.FileType("r"))
        parser.add_argument("--live", action="store_true")
        args = parser.parse_args()
        test = not args.live
        cache = args.cache and "with" or "without"
        mode = args.live and "live" or "test"
        cls.logger.info("running in %s mode %s cache", mode, cache)
        if args.session:
            uid, pwd = args.session, None
        else:
            uid, pwd = args.user, args.password
        control = cls(args.cache)
        comment = "Replace redirected and mobile URLs (OCECDR-4222)"
        job = ModifyDocs.Job(uid, pwd, control, control, comment,
                             validate=True, testMode=test)
        control.job = job
        job.run()
        elapsed = (datetime.datetime.now() - start).total_seconds()
        cls.logger.info("finished in %s seconds", elapsed)

Control.main()
