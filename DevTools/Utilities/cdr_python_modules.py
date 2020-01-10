#!/usr/bin/env python
#----------------------------------------------------------------------
#
# Finds all of the import statements in all of the Python scripts in
# a specified portion of the file system and reports any imported
# modules that we can't account for. This script identifies the
# following categories of Python modules used in the CDR system:
#  * standard library modules (e.g., sys)
#  * modules supplied by Active State's distribution (Windows and TK)
#  * other third-party modules (e.g., lxml)
#  * custom modules we've built ourselves
#
# Any imported module not included in one of these known sets will
# be reported.
#
# Usage:
#    find-unknown-python-modules.py [top-directory]
#
# A second optional usage passes a second argument specifying the
# name of a module. When invoked with this extra argument the script
# will instead report all of the Python scripts and modules which
# import the named module. This can be useful for identifying scripts
# which are obsolete (e.g., they import modules which are no longer
# installed, which is a clue that they're no longer used). For example:
#
#    find-unknown-python-modules.py . xml.parsers.xmlproc
#
#----------------------------------------------------------------------

import argparse
import ast
import os
import sys
import datetime

#----------------------------------------------------------------------
# These are the standard library modules known to be used by the CDR.
#----------------------------------------------------------------------
standard_library_modules = {
    "argparse",
    "ast",
    "atexit",
    "base64",
    "binascii",
    "builtins",
    "bz2",
    "calendar",
    "cgi",
    "cgitb",
    "concurrent", # from futures - used by ndscheduler
    "copy",
    "csv",
    "ctypes",
    "datetime",
    "difflib",
    "distutils.command.clean", # used by ndscheduler
    "email",
    "email.Header",
    "email.header",
    "email.message",
    "email.MIMEText",
    "email.mime.audio",
    "email.mime.base",
    "email.mime.image",
    "email.mime.multipart",
    "email.mime.text",
    "email.utils",
    "filecmp",
    "ftplib",
    "functools",
    "getopt",
    "getpass",
    "glob",
    "gzip",
    "hashlib",
    "html",
    "HTMLParser",
    "httplib",
    "importlib", # used by ndscheduler
    "io",
    "json",
    "locale",
    "logging",
    "logging.config",
    "logging.handlers",
    "math",
    "mimetypes",
    "msvcrt", # part of standard library, but only available on MS Windows
    "multiprocessing",
    "operator",
    "optparse",
    "os",
    "os.path",
    "pdb",
    "pickle",
    "platform",
    "pprint",
    "random",
    "re",
    "shutil",
    "signal",
    "six",
    "smtplib",
    "socket",
    "struct",
    "string",
    "subprocess",
    "sys",
    "tarfile",
    "tempfile",
    "textwrap",
    "threading",
    "time",
    "tkFileDialog",
    "Tkinter",
    "tkMessageBox",
    "traceback",
    "unittest",
    "urllib",
    "urllib.error",
    "urllib.parse",
    "urllib.request",
    "urllib2",
    "urllib3.exceptions",
    "urlparse",
    "uuid",
    "warnings",
    "webbrowser",
    "xml.dom.minidom",
    "xml.etree.ElementTree",
    "xml.etree.cElementTree",
    "xml.parsers.expat",
    "xml.sax",
    "xml.sax.handler",
    "xml.sax.saxutils",
    "zipfile",
}

#----------------------------------------------------------------------
# Other third-party modules used by the CDR. For modules without a
# URL in a comment, see the closest comment above the module.
#----------------------------------------------------------------------
third_party_modules = {
    "apscheduler.executors", # https://pypi.python.org/pypi/APScheduler
    "apscheduler.jobstores", # (sits underneath ndscheduler)
    "apscheduler.schedulers",
    "dateutil.parser", # https://pypi.python.org/pypi/python-dateutil
    "dateutil.tz",     #  (used by ndscheduler)
    "dateutil.relativedelta",
    "Image",           # https://python-pillow.org/
    "ImageEnhance",
    "lxml",            # http://lxml.de/
    "lxml.etree",
    "lxml.html",
    "lxml.html.builder",
    "mutagen",         # https://github.com/quodlibet/mutagen (replace MP3Info)
    # "MP3Info",         # http://www.lab49.com/~vivake/python/MP3Info.py
                       # (but not currently maintained, so we have it
                       # in subversion in lib/Python)
    "ndscheduler",     # https://github.com/Nextdoor/ndscheduler
    "ndscheduler.core",
    "ndscheduler.core.datastore",
    "ndscheduler.core.datastore.providers",
    "ndscheduler.core.scheduler",
    "ndscheduler.server",
    "ndscheduler.server.handlers",
    "PIL",             # https://python-pillow.org/
    "pip",             # https://pypi.python.org/pypi/pip
    "paramiko",        # http://www.paramiko.org/
    "pkg_resources",   # https://setuptools.readthedocs.io/en/latest/index.html
    "psutil",          # https://github.com/giampaolo/psutil (used by scheduler)
    "pymssql",         # http://www.pymssql.org (used by ndscheduler)
    "pyodbc",          # https://github.com/mkleehammer/pyodbc (db api)
    "pytz",            # https://pypi.python.org/pypi/pytz (used by ndscheduler)
    "requests",        # http://requests.readthedocs.io/en/master/ (HTTP api)
    "requests.packages.urllib3.exceptions",
    "setuptools",      # https://pypi.python.org/pypi/setuptools
                       # (used by ndscheduler)
    "sqlalchemy",      # http://www.sqlalchemy.org/ (DB API for scheduler)
    "sqlalchemy.pool",
    "tornado",         # http://www.tornadoweb.org (web server for scheduler)
    "tornado.concurrent",
    "tornado.gen",
    "tornado.ioloop",
    "tornado.platform.select",
    "tornado.testing",
    "tornado.web",
    "xlsxwriter",
    "xlrd",            # http://www.python-excel.org/
    "xlwt",
}

#----------------------------------------------------------------------
# Modules implemented specifically for the CDR project.
#----------------------------------------------------------------------
custom_modules = {
    "AssignGroupNums", # imported by cdrpub module
    "cdr",             # used throughout system
    "cdr2gk",          # used by Publishing subsystem (to communicate with GK)
    "cdrapi",          # replaces C++ server
    "cdrapi.db",
    "cdrapi.docs",
    "cdrapi.publishing",
    "cdrapi.reports",
    "cdrapi.searches",
    "cdrapi.settings",
    "cdrapi.users",
    "cdr_commands",    # CDR tunneling for client/server APIs
    "cdr_dev_data",    # used by scripts to preserve DEV data after refresh
    "cdr_job_base",    # part of CDR scheduler
    "cdr_task_base",
    "cdr_stats",       # management report on CDR statistics
    "cdrbatch",        # used for queueing up long-running jobs
    "cdrcgi",          # used by CDR administrative web interface
    "cdrdocobject",    # classes representing CDR document of specific types
    "cdrlite",         # stripped-down version of cdr module for secure login
    "CdrLongReports",  # reports that exceed the web server timeout
    "cdrmailer",       # used by mailer subsystem
    "cdrpub",          # used by publishing subsystem
    "cdrpw",           # interface to file containing system passwords
    "core.const",      # part of CDR scheduler
    "core.exceptions",
    "mock",            # https://pypi.python.org/pypi/mock
                       # (unit testing for ndscheduler)
    "ModifyDocs",      # used extensively by global change jobs
    "nci_thesaurus",   # used by scripts dealing with terminology documents
    "RepublishDocs",   # imported by CGI script Republish.py
    "RtfWriter",       # used by mailer subsystem
    "task_property_bag", # part of CDR scheduler
    "util.cdr_connection_info", # part of CDR scheduler
    "WebService",      # used by glossify and ClientRefresh services
}

#----------------------------------------------------------------------
# Determine whether a file could be a Python file based on its name.
# Basically if the file name has an extension, that extension must
# be .py or .pyw to be a Python source file (in this context).
# If the file name has no extension, and does not end in a tilde
# character (used by many editors to denote a backup file), then
# the file could be a Python file.
#----------------------------------------------------------------------
def might_be_python(name):
    if name == "glossify":
        return True
    if name.endswith("~"):
        return False
    if "." not in name:
        return True
    lower = name.lower()
    return lower.endswith(".py") or lower.endswith(".pyw")

#----------------------------------------------------------------------
# Return a string describing the type of module a name represents,
# based on membership in one of the sets above. If we end up using
# a module we've never used before, we'll modify the approriate set
# to include that module (not likely to happen very often).
#----------------------------------------------------------------------
def mod_type(name):
    if name in standard_library_modules:
        return "standard library"
    if name in third_party_modules:
        return "other third-party"
    if name in custom_modules:
        return "custom"
    return "unknown"

#----------------------------------------------------------------------
# Determine whether we already know about the origin of a named module.
#----------------------------------------------------------------------
def is_unknown(name):
    if name in standard_library_modules:
        return False
    if name in third_party_modules:
        return False
    if name in custom_modules:
        return False
    return True

#----------------------------------------------------------------------
# Generate the requested report.
#----------------------------------------------------------------------
def main():

    # Initialize the local variables, some from the command line arguments.
    modules = {}
    start_time = datetime.datetime.now()
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", default=".")
    parser.add_argument("--target")
    parser.add_argument("--counts", action="store_true")
    parser.add_argument("--show-unused", action="store_true")
    opts = parser.parse_args()
    opts.target = opts.target
    parsed = 0
    total = 0
    if opts.show_unused:
        used = set()

    # Walk through all of the files in the subtree of the file system.
    for base, dirs, files in os.walk(opts.directory):
        if ".svn" in base or ".git" in base:
            continue # older version of SVN have crap all over the place
        total += len(files)
        for name in files:
            if might_be_python(name):
                path = f"{base}/{name}".replace("\\", "/")
                #print("parsing", path)
                try:
                    with open(path) as fp:
                        source = fp.read()
                except Exception as e:
                    print(f"{path!r}: {e}")
                    continue
                if "import " not in source:
                    continue
                try:
                    tree = ast.parse(source)
                except:
                    print(f"{path!r} is not a Python 3 file")
                    raise
                parsed += 1
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if opts.show_unused:
                                used.add(alias.name)
                            #print("import", alias.name)
                            if opts.target:
                                if alias.name == opts.target:
                                    print(path)
                            else:
                                modules[alias.name] = modules.get(alias.name,
                                                                  0) + 1
                    elif isinstance(node, ast.ImportFrom):
                        if opts.show_unused:
                            used.add(node.module)
                        #print(f"from {node.module} import ...")
                        if opts.target:
                            if node.module == opts.target:
                                print(path)
                        else:
                            modules[node.module] = modules.get(node.module,
                                                               0) + 1

    # Write the report to the standard output.
    elapsed = datetime.datetime.now() - start_time
    if opts.counts:
        names = sorted(modules, key=lambda k: (modules[k], k.lower()))
        for name in names:
            print(f"{modules[name]:5d} {name:>30} ({mod_type(name)} module)")
    elif not opts.target:
        for name in sorted(modules):
            if is_unknown(name):
                print(name)
        if opts.show_unused:
            unused = standard_library_modules - used
            if unused:
                print("*** UNUSED STANDARD LIBRARY MODULES ***")
                for name in sorted(unused):
                    print(name)
            unused = third_party_modules - used
            if unused:
                print("*** UNUSED THIRD-PARTY MODULES ***")
                for name in sorted(unused):
                    print(name)
            unused = custom_modules - used
            if unused:
                print("*** UNUSED CUSTOM MODULES ***")
                for name in sorted(unused):
                    print(name)
    print(f"{parsed:d} scripts parsed in {elapsed.total_seconds()} seconds")
    print(f"{total:d} files examined")

#----------------------------------------------------------------------
# Only run the report if the file is loaded as a script (instead of
# as a module).
#----------------------------------------------------------------------
if __name__ == "__main__":
    main()
