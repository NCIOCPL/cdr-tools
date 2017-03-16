#!/usr/bin/env python
#----------------------------------------------------------------------
# Fetch server settings for the CDR tiers and optionally report on
# the differences between pairs of tiers. Run with --help for options.
# OCECDR-4101
#----------------------------------------------------------------------
import argparse
import datetime
import difflib
import getpass
import json
import requests
import sys
import xlwt

class TierSettings:
    """
    Collection of settings for a single CDR tier's servers

    STAMP - string identifying the current time to the second
    TIERS - valid values for tier argument
    """

    STAMP = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    TIERS = ("PROD", "STAGE", "QA", "DEV")

    def __init__(self, tier, source):
        """
        Remember the tier and load its settings.
        """

        self.tier = tier
        self.info = self.load(source)

    def load(self, source):
        """
        Fetch the dictionary of settings from its JSON serialization.

        If source is a path for a readable file, load the tier's
        settings from that file. Otherwise, connect to the Windows
        server for the tier and request the settings, using the
        source parameter as the CDR Session ID for the server.
        """

        try:
            fp = open(source, "rb")
            self.json = fp.read()
            fp.close()
        except:
            host = self.get_host(self.tier)
            url = "https://%s/cgi-bin/cdr/fetch-tier-settings.py" % host
            data = { "Session": source }
            response = requests.get(url, data)
            self.json = response.text
            self.save()
        return json.loads(self.json)

    def save(self):
        """
        Write the json-serialized settings to a disk file.

        The file name contains the tier namd and a time stamp,
        with resolution to the second.
        """

        name = "tier-settings.%s.%s" % (self.tier, self.STAMP)
        fp = open(name, "wb")
        fp.write(self.json)
        fp.close()
        print "saved %s" % name

    def get_value(self, path):
        """
        Walk through the settings dictionary to find a specific value.

        The keys for the nested dictionaries are separated by a forward
        slash.
        """

        values = self.info
        for key in path.split("/"):
            values = values.get(key)
            if values is None:
                break
        if isinstance(values, basestring):
            if path.endswith("environ/DOCUMENT_ROOT"):
                values = values.rstrip("/")
        return values

    @staticmethod
    def get_host(tier):
        """
        Get the FQDN for this tier's Windows server.
        """

        host = "cdr-%s" % tier.lower()
        if host == "cdr-prod":
            host = "cdr"
        return "%s.cancer.gov" % host

    @staticmethod
    def logon(tier, user, password):
        """
        Create a new CDR session and return its session ID.
        """

        host = TierSettings.get_host(tier)
        url = "https://%s/cgi-bin/secure/login.py" % host
        requests.packages.urllib3.disable_warnings()
        auth = requests.auth.HTTPDigestAuth(user, password)
        response = requests.get(url, auth=auth, verify=False)
        return response.text.strip()

    @staticmethod
    def get_args():
        """
        Fetch the command-line arguments and explain how to run the script.
        """

        parser = argparse.ArgumentParser(description="Compare cdr tiers",
                                         epilog="""\
If a single tier is named, its settings will be fetched and saved to
a file whose name contains the tier and a timestamp. If more than one
tier is named, the settings will be saved in separate files as for
a single tier, and in addition each adjacent pair of tiers will be
compared and the differences reported in an worksheet, to be saved
as part of a single Excel workbook (with a timestamped file name).
You can specify a password on the command line, but this is discouraged
as insecure. If you supply a user name but no password (the most common
usage) you will be prompted for a password, which will not be displayed
as you type it.

For some or all of the tiers, you may follow the tier name with a
file path identifying settings for a tier captured from a previous
run of the program. Separate the tier name from the path with a colon.
You can also provide a CDR session ID for each tier instead of giving
your CDR user name and password. Each tier must have its own session
ID, valid for that tier, and the session ID is separated from the
tier name by a colon.""")
        parser.add_argument("tier", nargs="+", choices=TierSettings.TIERS)
        parser.add_argument("-u", "--user", help="NIH domain user ID")
        parser.add_argument("-p", "--password", help="NIH domain password")
        return parser.parse_args()

    @staticmethod
    def run():
        """
        Collect the tier settings and optionally compare pairs of tie
        """

        args = TierSettings.get_args()
        if args.user:
            password = args.password
            if not password:
                prompt = "CDR password for %s: " % args.user
                password = getpass.getpass(prompt)
        tiers = []
        for tier in args.tier:
            if ":" in tier:
                tier, source = tier.split(":")
                tier = tier.upper()
            else:
                tier = tier.upper()
                if not args.user:
                    raise Exception("must supply credentials or file name")
                source = TierSettings.logon(tier, args.user, password)
            tiers.append(TierSettings(tier, source))
        if len(tiers) > 1:
            Report(tiers).save(TierSettings.STAMP)

class Report:
    """
    Logic for generating an Excel workbook with a separate worksheet
    for each pair of tiers being compared.

    PATHS - portions of the collected settings which should be compared
    SKIP - skip over these elements/paths
    MAX_REPR_LEN - used to shorted long representations of lists/dicts
    PATH_WIDTH - width of the first worksheet column
    VALUE_WIDTH - width of the second and third worksheet columns
    """

    LINUX_PATHS = (
        "environ/SERVER_SOFTWARE",
        "environ/SERVER_PROTOCOL",
        "environ/PATH",
        "environ/LD_LIBRARY_PATH",
        "environ/DOCUMENT_ROOT",
        "environ/PYTHONPATH",
        "environ/HTTP_ACCEPT_ENCODING",
        "files",
        "hosts",
        "mysql",
        "python",
        "release",
    )
    WINDOWS_PATHS = (
        "doctypes",
        "environ/SERVER_SOFTWARE",
        "environ/PROCESSOR_IDENTIFIER",
        "environ/PROCESSOR_REVISION",
        "environ/PROCESSOR_ARCHITECTURE",
        "environ/PROCESSOR_LEVEL",
        "environ/NUMBER_OF_PROCESSORS",
        "environ/TZ",
        "environ/SERVER_PROTOCOL",
        "environ/PYTHONPATH",
        "environ/HTTP_ACCEPT_ENCODING",
        "environ/GATEWAY_INTERFACE",
        "files/cdr/Bin",
        "files/cdr/ClientFiles",
        "files/cdr/lib",
        "files/cdr/Licensee",
        "files/cdr/Mailers",
        "files/cdr/Publishing",
        "files/cdr/",
        "files/Inetpub/wwwroot/CdrFilter.html",
        "files/Inetpub/wwwroot/cgi-bin",
        "files/Inetpub/wwwroot/images",
        "files/Inetpub/wwwroot/js",
        "files/Inetpub/wwwroot/stylesheets",
        "files/Inetpub/wwwroot/web.config",
        "files/usr",
        "iis",
        "mssql/TX_ISOLATION",
        "mssql/COLLATION_SEQ",
        "mssql/SYS_SPROC_VERSION",
        "mssql/IDENTIFIER_CASE",
        "mssql/DBMS_VER",
        "python",
        "search_path",
        "version",
    )
    PATHS = tuple(
        ["emailers/" + path for path in LINUX_PATHS] +
        ["glossifier/" + path for path in LINUX_PATHS] +
        ["windows/" + path for path in WINDOWS_PATHS]
    )

    SKIP_LINUX = (
        "mysql/innodb_data_home_dir",
        "mysql/innodb_open_files",
        "mysql/datadir",
        "mysql/general_log_file",
        "mysql/hostname",
        "mysql/innodb_log_group_home_dir",
        "mysql/log_error",
        "mysql/pid_file",
        "mysql/pseudo_thread_id",
        "mysql/server_uuid",
        "mysql/slow_query_log_file",
        "mysql/socket",
        "mysql/timestamp",
        "mysql/open_files_limit",
        "mysql/performance_schema_digests_size",
        "mysql/performance_schema_events_stages_history_long_size",
        "mysql/performance_schema_events_statements_history_long_size",
        "mysql/performance_schema_events_waits_history_long_size",
        "mysql/performance_schema_max_cond_instances",
        "mysql/performance_schema_max_file_instances",
        "mysql/performance_schema_max_mutex_instances",
        "mysql/performance_schema_max_rwlock_instances",
        "mysql/performance_schema_max_socket_instances",
        "mysql/performance_schema_max_table_handles",
        "mysql/performance_schema_max_table_instances",
        "mysql/performance_schema_max_thread_instances",
        "mysql/table_definition_cache",
        "mysql/table_open_cache",
        "files/web/glossifier/wwwroot/index.html",
    )
    SKIP_WINDOWS = (
        "files/cdr/lib/tmp",
        "files/cdr/ClientFiles/CdrManifest.xml",
        "files/cdr/ClientFiles/CdrDocTypes.xml",
        "files/Inetpub/wwwroot/cgi-bin/broken-scheduler",
        "files/Inetpub/wwwroot/cgi-bin/cdr/CheckDevData.py",
        "iis/account"
    )
    SKIP = set(
        ["emailers/%s" % skip for skip in SKIP_LINUX] +
        ["glossifier/%s" % skip for skip in SKIP_LINUX] +
        ["windows/%s" % skip for skip in SKIP_WINDOWS]
    )

    MAX_REPR_LEN = 75
    PATH_WIDTH = 20000
    VALUE_WIDTH = 20000

    DEV_PATHS = set([
        r"d:\usr\emacs\bin",
        r"d:\usr\vim\vim80",
        r"c:\program files (x86)\microsoft sql server\100\tools\binn",
        r"c:\program files\microsoft sql server\110\tools\binn",
        r"c:\program files\microsoft sql server\100\dts\binn",
        r"c:\program files (x86)\microsoft sql server\100\tools\binn"
        r"\vsshell\common7\ide",
        r"c:\program files (x86)\microsoft sql server\100\dts\binn",
        r"c:\program files\tortoisesvn\bin",
        r"c:\program files (x86)\windows kits\8.1"
        r"\windows performance toolkit",
        r"c:\program files (x86)\microsoft sdks\typescript\1.0"
    ])
    xlwt.add_palette_colour("hdrbg", 0x21)

    def __init__(self, tiers):
        """
        Create the Excel workbook for the report and populated it.
        """

        self.tiers = tiers
        self.wb = xlwt.Workbook(encoding="UTF-8")
        self.wb.set_colour_RGB(0x21, 153, 52, 102) #993366
        self.data_style = self.make_style()
        self.header_style = self.make_style(header=True)
        for position in range(1, len(tiers)):
            self.compare(tiers[position - 1], tiers[position])

    def make_style(self, **opts):
        """
        Create an style object usable by the xlwt module.
        """

        settings = {
            "borders": "top thin, bottom thin, left thin, right thin",
            "align": "wrap True, vert top, horiz left"
        }
        if opts.get("header"):
            settings["font"] = "colour white, bold True"
            settings["pattern"] = "pattern solid, fore_colour hdrbg"
            settings["align"] = "wrap True, vert centre, horiz centre"
        settings = ";".join(["%s: %s" % (k, settings[k]) for k in settings])
        return xlwt.easyxf(settings)

    def save(self, stamp):
        """
        Write the Excel workbook to a timestamped file.
        """

        name = "tier-settings-%s.xls" % stamp
        fp = open(name, "wb")
        self.wb.save(fp)
        fp.close()
        print "saved", name

    def compare(self, s1, s2):
        """
        Top-level driver to compare each path in Report.PATHS between tiers.
        """

        name = "%s--%s" % (s1.tier, s2.tier)
        self.sheet = self.wb.add_sheet(name)
        self.sheet.col(0).width = self.PATH_WIDTH
        self.sheet.col(1).width = self.VALUE_WIDTH
        self.sheet.col(2).width = self.VALUE_WIDTH
        self.sheet.write(0, 0, "Element", self.header_style)
        self.sheet.write(0, 1, s1.tier, self.header_style)
        self.sheet.write(0, 2, s2.tier, self.header_style)
        self.row_number = 1
        for path in self.PATHS:
            self.check_path(path, s1, s2)

    def check_path(self, path, s1, s2):
        """
        Top-level function to compare a portion of the settings dictionaries.
        """

        v1 = s1.get_value(path)
        v2 = s2.get_value(path)
        self.compare_nodes(path, v1, v2)

    def compare_nodes(self, path, v1, v2):
        """
        Compare and report on a node in two tiers' settings dictionaries.

        Indirectly recursive.
        """
        if v1 != v2:
            if v1 is None or v2 is None:
                self.add_row(path, v1, v2)
            elif isinstance(v1, basestring) and isinstance(v2, basestring):
                self.add_row(path, v1, v2)
            elif type(v1) != type(v2):
                self.add_row(path, v1, v2)
            elif isinstance(v1, dict):
                self.check_dicts(path, v1, v2)
            elif isinstance(v1, list):
                self.check_lists(path, v1, v2)
            else:
                error = "%s: unexpected value type %s" % (path, type(v1))
                raise Exception(error)

    def add_row(self, path, v1, v2):
        """
        Add a row to the current Excel worksheet.

        Skip over compiled Python modules, and editor backup files.
        """

        path_lower = path.lower()
        for ending in (".pyc", "py~", "/dada.py"):
            if path_lower.endswith(ending):
                return
        self.add_cell(0, path)
        self.add_cell(1, v1)
        self.add_cell(2, v2)
        self.row_number += 1

    def add_cell(self, col, val):
        """
        Add a cell to the Excel worksheet, collapsing complex values.
        """

        if type(val) in (dict, list):
            val = repr(val)
            if len(val) > self.MAX_REPR_LEN:
                val = val[:self.MAX_REPR_LEN] + " ..."
        if not isinstance(val, basestring):
            val = str(val)
        self.sheet.write(self.row_number, col, val, self.data_style)

    def check_dicts(self, path, d1, d2):
        """
        Compare the items in two dictionaries (indirectly recursive)
        """

        for key in sorted(d1):
            this_path = "%s/%s" % (path, key)
            if this_path not in self.SKIP:
                v1, v2 = d1.get(key), d2.get(key)
                self.compare_nodes(this_path, v1, v2)
        for key in sorted(d2):
            if key not in d1:
                this_path = "%s/%s" % (path, key)
                if this_path not in self.SKIP:
                    self.add_row(this_path, None, d2.get(key))

    def prune_search_path(self, values):
        new_values = []
        for value in values:
            value = value.rstrip("\\")
            if value.lower() not in self.DEV_PATHS:
                new_values.append(value)
        return new_values

    def check_lists(self, path, v1, v2):
        """
        Compare two ordered sequences of values.
        """
        if path == "windows/search_path":
            v1 = self.prune_search_path(v1)
            v2 = self.prune_search_path(v2)
        if path not in self.SKIP and v1 != v2:
            v1 = "\n".join([unicode(v) for v in v1])
            v2 = "\n".join([unicode(v) for v in v2])
            self.add_row(path, v1, v2)
        return
        differ = difflib.Differ()
        result = list(differ.compare(v1, v2))
        differences = False
        for line in result:
            if line[0] in ("+-"):
                differences = True
                break
        if differences:
            for line in result:
                value = line[2:]
                if line[0] in "+- ":
                    if line[0] == "+":
                        print "%s\t\t%s" % (path, value)
                    elif line[0] == "-":
                        print "%s\t%s\t" % (path, value)
                    elif line[0] == " ":
                        print "%s\t%s\t%s" % (path, value, value)
                    path = ""

if __name__ == "__main__":
    """
    Make it possible to load this as a module without running it.
    """
    TierSettings.run()
