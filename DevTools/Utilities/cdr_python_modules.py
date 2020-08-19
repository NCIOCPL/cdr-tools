#!/usr/bin/env python
#----------------------------------------------------------------------
#
# Finds all of the import statements in all of the Python scripts in
# a specified portion of the file system and reports any imported
# modules that we can't account for. This script identifies the
# following categories of Python modules used in the CDR system:
#  * standard library modules (e.g., sys)
#  * other third-party modules (e.g., lxml)
#  * custom modules we've built ourselves
#
# Any imported module not included in one of these known sets will
# be reported.
#
# By default, the script starts with the current working directory
# as the top of the portion of the file system to examine. The
# --directory option can override that default.
#
# The --target option can identify a module, which will cause the
# script to report all of the scripts and modules which import the
# named module. This can be useful for identifying scripts which
# are obsolete (e.g., they import modules which are no longer
# installed, which is a clue that they're no longer used). For example:
#
#    cdr-python-modules.py --target xml.parsers.xmlproc
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
    "calendar",
    "cgi",
    "cgitb",
    "collections",
    "copy",
    "csv",
    "ctypes",
    "datetime",
    "difflib",
    "email",
    "email.message",
    "email.mime.audio",
    "email.mime.base",
    "email.mime.image",
    "email.mime.multipart",
    "email.mime.text",
    "email.utils",
    "ftplib",
    "functools",
    "getopt",
    "getpass",
    "glob",
    "gzip",
    "hashlib",
    "html",
    "importlib", # used by ndscheduler
    "io",
    "json",
    "locale",
    "logging",
    "mimetypes",
    "msvcrt", # part of standard library, but only available on MS Windows
    "operator",
    "optparse",
    "os",
    "os.path",
    "platform",
    "pprint",
    "random",
    "re",
    "shutil",
    "six",
    "smtplib",
    "socket",
    "string",
    "subprocess",
    "sys",
    "tarfile",
    "tempfile",
    "textwrap",
    "threading",
    "time",
    "traceback",
    "unicodedata",
    "unittest",
    "urllib.error",
    "urllib.parse",
    "urllib.request",
    "urllib2",
    "urllib3.exceptions",
    "webbrowser",
    "xml.dom.minidom",
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
    "apscheduler.schedulers.background",
        # https://pypi.python.org/pypi/APScheduler
    "dateutil.parser", # https://pypi.python.org/pypi/python-dateutil
    "dateutil.relativedelta",
    "elasticsearch5",
    "lxml",            # http://lxml.de/
    "lxml.etree",
    "lxml.html",
    "lxml.html.builder",
    "mutagen.mp3",     # https://github.com/quodlibet/mutagen (replace MP3Info)
    # "MP3Info",         # http://www.lab49.com/~vivake/python/MP3Info.py
                       # (but not currently maintained, so we have it
                       # in subversion in lib/Python)
    "openpyxl",        # https://pypi.org/project/openpyxl/
    "openpyxl.styles",
    "openpyxl.utils",
    "PIL",             # https://python-pillow.org/
    "paramiko",        # http://www.paramiko.org/
    "pkg_resources",   # https://setuptools.readthedocs.io/en/latest/index.html
    "pyodbc",          # https://github.com/mkleehammer/pyodbc (db api)
    "requests",        # http://requests.readthedocs.io/en/master/ (HTTP api)
    "requests.packages.urllib3.exceptions",
    "xlsxwriter",
    "xlrd",            # http://www.python-excel.org/
    "xlwt",
}

#----------------------------------------------------------------------
# Modules implemented specifically for the CDR project.
#----------------------------------------------------------------------
custom_modules = {
    "base_job",        # for rewritten scheduler
    "cdr",             # used throughout system
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
    "dictionary_loader", # population of ElasticSearch dictionary databases
    "ModifyDocs",      # used extensively by global change jobs
    "nci_thesaurus",   # used by scripts dealing with terminology documents
    "RepublishDocs",   # imported by CGI script Republish.py
    "RtfWriter",       # used by mailer subsystem
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
