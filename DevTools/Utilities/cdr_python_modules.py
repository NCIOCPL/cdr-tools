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

import ast
import os
import sys
import time

#----------------------------------------------------------------------
# These are the standard library modules known to be used by the CDR.
#----------------------------------------------------------------------
standard_library_modules = set([
    "argparse",
    "ast",
    "atexit",
    "base64",
    "builtins",
    "bz2",
    "calendar",
    "cgi",
    "cgitb",
    "codecs",
    "concurrent", # from futures - used by ndscheduler
    "copy",
    "cPickle",
    "csv",
    "cStringIO",
    "ctypes",
    "datetime",
    "difflib",
    "distutils.command.clean", # used by ndscheduler
    "email",
    "email.Header",
    "email.MIMEText",
    "email.mime.audio",
    "email.mime.base",
    "email.mime.image",
    "email.mime.multipart",
    "email.mime.text",
    "email.utils",
    "filecmp",
    "ftplib",
    "getopt",
    "glob",
    "gzip",
    "hashlib",
    "HTMLParser",
    "httplib",
    "importlib", # used by ndscheduler
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
    "random",
    "re",
    "shutil",
    "signal",
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
    "urllib2",
    "urlparse",
    "uuid",
    "warnings",
    "xml.dom.minidom",
    "xml.etree.ElementTree",
    "xml.etree.cElementTree",
    "xml.parsers.expat",
    "xml.sax",
    "xml.sax.handler",
    "xml.sax.saxutils",
    "zipfile",
])

#----------------------------------------------------------------------
# These are non-standard modules used by the CDR and provided as part
# of ActiveState's Python distribution for use on Windows platforms.
# See http://www.activestate.com/activepython.
#----------------------------------------------------------------------
active_state_modules = set([
    "pythoncom",
    "pywintypes",
    "win32com.client",
    "win32file",
])

#----------------------------------------------------------------------
# Other third-party modules used by the CDR. For modules without a
# URL in a comment, see the closest comment above the module.
#----------------------------------------------------------------------
third_party_modules = set([
    "apns",            # https://github.com/djacobs/PyAPNs (for scheduler)
    "dateutil.parser", # https://pypi.python.org/pypi/python-dateutil
    "dateutil.tz",     #  (used by ndscheduler)
    "Image",           # http://www.pythonware.com/products/pil/
    "ImageEnhance",
    "lxml",            # http://lxml.de/
    "lxml.etree",
    "lxml.html",
    "lxml.html.builder",
    "MP3Info",         # http://www.lab49.com/~vivake/python/MP3Info.py
                       # (but not currently maintained, so we have it
                       # in subversion in lib/Python)
    "MySQLdb",         # http://sourceforge.net/projects/mysql-python/
    "pip",             # https://pypi.python.org/pypi/pip
    "xlrd",            # http://www.python-excel.org/
    "xlwt",
    "paramiko",        # http://www.paramiko.org/
    "requests",        # http://requests.readthedocs.io/en/master/ (HTTP api)
    "setuptools",      # https://pypi.python.org/pypi/setuptools
                       # (used by ndscheduler)
    "sqlalchemy",      # http://www.sqlalchemy.org/ (DB API for scheduler)
    "suds.client",     # http://sourceforge.net/projects/python-suds/
    "tornado",         # http://www.tornadoweb.org (web server for scheduler)
    "tornado.concurrent",
    "tornado.gen",
    "tornado.ioloop",
    "tornado.testing",
    "tornado.web"
])

#----------------------------------------------------------------------
# Modules implemented specifically for the CDR project.
#----------------------------------------------------------------------
custom_modules = set([
    "apscheduler.executors", # https://pypi.python.org/pypi/APScheduler
    "apscheduler.jobstores", # (sits underneath ndscheduler)
    "apscheduler.schedulers",
    "AssignGroupNums", # imported by cdrpub module
    "authmap",         # used by ebms/conversion/convert.py (in same directory)
    "BuildDeploy",     # used by CDR build/deploy scripts
    "cdr",             # used throughout system
    "cdr2gk",          # used by Publishing subsystem (to communicate with GK)
    "cdr_dev_data",    # used by scripts to preserve DEV data after refresh
    "cdr_job_base",    # part of CDR scheduler
    "cdr_task_base",
    "cdrbatch",        # used for queueing up long-running jobs
    "cdrcgi",          # used by CDR administrative web interface
    "cdrdb",           # used throughout system for DB access
    "cdrdocobject",    # classes representing CDR document of specific types
    "cdrglblchg",      # common routines for global change jobs
    "cdrlatexlib",     # used by mailer subsystem
    "cdrlatextables",  # used by mailer subsystem
    "cdrlite",         # stripped-down version of cdr module for secure login
    "cdrmailcommon",   # used by mailer subsystem
    "cdrmailer",       # used by mailer subsystem
    "cdrpub",          # used by publishing subsystem
    "cdrpubcgi",       # used by publishing subsystem
    "cdrpw",           # interface to file containing system passwords
    "cdrutil",         # abstractions of platform characteristics
    "cdrxdiff",        # used by batch jobs to compare documents
    "cdrxmllatex",     # used by mailer subsystem
    "CgiQuery",        # used by CGI script CdrQueries.py (for ad hoc SQL)
    "core.const",      # part of CDR scheduler
    "core.exceptions",
    "CTGovUpdateCommon", # used by scripts for clinical trial docs from NLM
    "EmailerLookupTables", # used by mailer subsystem (obsolete?)
    "EmailerProtSites", # used by the mailer subsystem (obsolete?)
    "get_stats",       # used by Production/prod/bin/SendEmail.py
    "GPFragIds",       # used by legacy conversion (not currently used)
    "GlobalChangeLinkBatch", # imported by CGI script GlobalChangeLink.py
    "GlossaryTermGroups", # imported by ConvertGlossaryDocs.py (not current)
    "mock",            # https://pypi.python.org/pypi/mock
                       # (unit testing for ndscheduler)
    "ModifyDocs",      # used extensively by global change jobs
    "nci_thesaurus",   # used by scripts dealing with terminology documents
    "ndscheduler",     # https://github.com/Nextdoor/ndscheduler
    "ndscheduler.core",
    "ndscheduler.core.datastore",
    "ndscheduler.core.datastore.providers",
    "ndscheduler.core.scheduler",
    "ndscheduler.server",
    "ndscheduler.server.handlers",
    "NewGPOrgs",       # used by legacy conversion (not currently used)
    "pdq_data_partner",# for managing PDQ data partner information
    "PdqThesaurus",    # obsolete, used by older one-off jobs back in 2009
    "pymssql",         # http://www.pymssql.org (used by ndscheduler)
    "pytz",            # https://pypi.python.org/pypi/pytz (used by ndscheduler)
    "RepublishDocs",   # imported by CGI script Republish.py
    "RtfWriter",       # used by mailer subsystem
    "task_property_bag", # part of CDR scheduler
    "UnicodeToLatex",  # used by mailer subsystem
    "unicode2ascii",   # used by legacy conversion (not currently used)
    "util",            # imported by MakeGPEmailerTables (historical only)
                       # (replaced by cdrutil module)
    "util.cdr_connection_info", # part of CDR scheduler
    "WebService",      # used by glossify and ClientRefresh services
])

#----------------------------------------------------------------------
# Determine whether a file could be a Python file based on its name.
# Basically if the file name has an extension, that extension must
# be .py or .pyw to be a Python source file (in this context).
# If the file name has no extension, and does not end in a tilde
# character (used by many editors to denote a backup file), then
# the file could be a Python file.
#----------------------------------------------------------------------
def might_be_python(name):
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
    if name in active_state_modules:
        return "Active State contributed"
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
    if name in active_state_modules:
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
    start_time = time.time()
    start_dir = len(sys.argv) > 1 and sys.argv[1] or "."
    search_for = len(sys.argv) > 2 and sys.argv[2] or None
    if search_for == "--counts":
        search_for = None
        counts = True
    else:
        counts = False
    parsed = 0
    total = 0

    # Walk through all of the files in the subtree of the file system.
    for base, dirs, files in os.walk(start_dir):
        if ".svn" in base:
            continue # older version of SVN have crap all over the place
        total += len(files)
        for name in files:
            if might_be_python(name):
                path = ("%s/%s" % (base, name)).replace("\\", "/")
                #print "parsing", path
                fp = open(path)
                source = fp.read()
                fp.close()
                if "import " not in source:
                    continue
                try:
                    tree = ast.parse(source)
                except:
                    #print "%s is not a Python file" % repr(path)
                    continue
                parsed += 1
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            #print "import", alias.name
                            if search_for:
                                if alias.name == search_for:
                                    print path
                            else:
                                modules[alias.name] = modules.get(alias.name,
                                                                  0) + 1
                    elif isinstance(node, ast.ImportFrom):
                        #print "from %s import ..." % node.module
                        if search_for:
                            if node.module == search_for:
                                print path
                        else:
                            modules[node.module] = modules.get(node.module,
                                                               0) + 1

    # Write the report to the standard output.
    elapsed = time.time() - start_time
    if counts:
        names = sorted(modules, key=lambda k: (modules[k], k.lower()))
        for name in names:
            print "%5d %-30s (%s module)" % (modules[name], name,
                                             mod_type(name))
    elif not search_for:
        for name in sorted(modules):
            if is_unknown(name):
                print name
    print "%d scripts parsed in %.3f seconds" % (parsed, elapsed)
    print "%d files examined" % total

#----------------------------------------------------------------------
# Only run the report if the file is loaded as a script (instead of
# as a module).
#----------------------------------------------------------------------
if __name__ == "__main__":
    main()
