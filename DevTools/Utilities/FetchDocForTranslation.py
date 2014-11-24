#----------------------------------------------------------------------
#
# $Id$
#
# Export CDR document XML for translation in World Server.
#
# JIRA::OCECDR-3783 - drop Comment elements
#
#----------------------------------------------------------------------
import cdr
import sys

#----------------------------------------------------------------------
# Check command-line arguments.
#----------------------------------------------------------------------
try:
    doc_id = int(sys.argv[1])
    version = len(sys.argv) > 2 and int(sys.argv[2]) or None
except:
    sys.stderr.write("usage: FetchDocForTranslation.py doc-id [doc-version]\n")
    sys.exit(1)

#----------------------------------------------------------------------
# Make sure we don't introduce changes to line endings.
#----------------------------------------------------------------------
if sys.platform == "win32":
    import os
    import msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

#----------------------------------------------------------------------
# Strip the comments.
#----------------------------------------------------------------------
xslt = ["name:Strip Comment Elements"]
response = cdr.filterDoc("guest", xslt, doc_id, docVer=version)
err = cdr.checkErr(response)
if err:
    sys.stderr.write(err)
else:
    sys.stdout.write(response[0])
