#!/usr/bin/python
#----------------------------------------------------------------------
#
# $Id$
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

modules = {}

def might_be_python(name):
    if name.endswith("~"):
        return False
    if "." not in name:
        return True
    lower = name.lower()
    return lower.endswith(".py") or lower.endswith(".pyw")

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
                        modules[node.module] = modules.get(node.module, 0) + 1

standard_library_modules = set([
    "ast",
    "atexit",
    "base64",
    "bz2",
    "calendar",
    "cgi",
    "cgitb",
    "codecs",
    "copy",
    "cPickle",
    "csv",
    "cStringIO",
    "datetime",
    "difflib",
    "email.Header",
    "email.MIMEText",
    "filecmp",
    "ftplib",
    "getopt",
    "glob",
    "gzip",
    "HTMLParser",
    "httplib",
    "locale",
    "operator",
    "optparse",
    "os",
    "os.path",
    "pdb",
    "pickle",
    "random",
    "re",
    "shutil",
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
    "urllib",
    "urllib2",
    "urlparse",
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

active_state_modules = set([
    "msvcrt",
    "pythoncom",
    "pywintypes",
    "win32com.client",
    "win32file",
])

third_party_modules = set([
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
    "xlrd",            # http://www.python-excel.org/
    "xlwt",
    "paramiko",        # http://www.paramiko.org/
    "suds.client",     # http://sourceforge.net/projects/python-suds/
])

custom_modules = set([
    "AssignGroupNums", # imported by cdrpub module
    "authmap",         # used by ebms/conversion/convert.py (in same directory)
    "cdr",             # used throughout system
    "cdr2gk",          # used by Publishing subsystem (to communicate with GK)
    "cdr_dev_data",    # used by scripts to preserve DEV data after refresh
    "cdrbatch",        # used for queueing up long-running jobs
    "cdrcgi",          # used by CDR administrative web interface
    "cdrdb",           # used throughout system for DB access
    "cdrdocobject",    # classes representing CDR document of specific types
    "cdrglblchg",      # common routines for global change jobs
    "cdrlatexlib",     # used by mailer subsystem
    "cdrlatextables",  # used by mailer subsystem
    "cdrmailcommon",   # used by mailer subsystem
    "cdrmailer",       # used by mailer subsystem
    "cdrpub",          # used by publishing subsystem
    "cdrpubcgi",       # used by publishing subsystem
    "cdrpw",           # interface to file containing system passwords
    "cdrutil",         # abstractions of platform characteristics
    "cdrxdiff",        # used by batch jobs to compare documents
    "cdrxmllatex",     # used by mailer subsystem
    "CgiQuery",        # used by CGI script CdrQueries.py (for ad hoc SQL)
    "CTGovUpdateCommon", # used by scripts for clinical trial docs from NLM
    "ctrp",            # used for import of clinical trial docs from CTRP
    "EmailerLookupTables", # used by mailer subsystem (obsolete?)
    "EmailerProtSites", # used by the mailer subsystem (obsolete?)
    "ExcelReader",     # don't use for future scripts (use xlrd instead)
    "ExcelWriter",     # don't use for future scripts (use xlwt instead)
    "extMapPatChk",    # common code for external mapping maintenance
    "get_stats",       # used by Production/prod/bin/SendEmail.py
    "GPFragIds",       # used by legacy conversion (not currently used)
    "GlobalChangeLinkBatch", # imported by CGI script GlobalChangeLink.py
    "GlossaryTermGroups", # imported by ConvertGlossaryDocs.py (not current)
    "ModifyDocs",      # used extensively by global change jobs
    "NCIThes",         # used by scripts dealing with terminology documents
    "NciThesaurus",    # original version of NCIThes, used by one-off job
    "NewGPOrgs",       # used by legacy conversion (not currently used)
    "OleStorage",      # imported by ExcelReader module
    "PdqThesaurus",    # obsolete, used by older one-off jobs back in 2009
    "RepublishDocs",   # imported by CGI script Republish.py
    "RtfWriter",       # used by mailer subsystem
    "SimpleLinkGlobalChangeBatch", # imported by CGI global change script
    "UnicodeToLatex",  # used by mailer subsystem
    "unicode2ascii",   # used by legacy conversion (not currently used)
    "util",            # imported by MakeGPEmailerTables (historical only)
                       # (replaced by cdrutil module)
    "WebService",      # used by glossify and ClientRefresh services
])

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

elapsed = time.time() - start_time
if counts:
    names = sorted(modules, key=lambda k: (modules[k], k.lower()))
    for name in names:
        print "%5d %-30s (%s module)" % (modules[name], name, mod_type(name))
elif not search_for:
    for name in sorted(modules):
        if is_unknown(name):
            print name
print "%d scripts parsed in %.3f seconds" % (parsed, elapsed)
print "%d files examined" % total
