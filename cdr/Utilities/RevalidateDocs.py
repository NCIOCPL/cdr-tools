####################################################################
# Validate some or all documents in the database.
#
# See usage() for parameters.
#
# $Id: RevalidateDocs.py,v 1.7 2007-02-02 01:21:14 ameyer Exp $
#
# $Log: not supported by cvs2svn $
# Revision 1.6  2007/01/30 23:51:06  ameyer
# Added logging of command line parameters.
#
# Revision 1.5  2007/01/30 21:50:13  ameyer
# Added counter for number of docs of each type, displayed at end.
#
# Revision 1.4  2007/01/26 04:29:27  ameyer
# Added summary of errors by doctype.
#
# Revision 1.3  2007/01/26 04:06:52  ameyer
# Added new parameters.
# Beefed up logging, now always goes to a file.
# Allow more than one specific doctypes to be requested, or specific ones
# to be excluded.
#
#
####################################################################

import sys, getopt, time, cdr, cdrdb

# Default is to report after every this many docs
RPT_COUNT = 1000

# Default log file
LOGFILE = 'RevalidateDocs.log'

####################################################################
# Display usage message and exit
####################################################################
def usage (msg):

    # Display passed message
    sys.stderr.write ("Error: %s\n" % msg)

    # Standard usage message
    sys.stderr.write ("""
usage: RevalidateDocs {options} userid password
 options:
  --schemaonly      = Only do schema validation, no links
  --linkonly        = Only do link validation, no schema
  --quiet           = No output, just do it in the server
                       If --noupdate nothing useful could happen
  --verbose         = Output id of every doc validated, else just outputs
                       id + messages of docs with errors
  --noupdate        = Do not update the database:
                       Date last validated will not be set
                       Last validation status will not be set
                       Link tables will not be updated
  --include name    = Only validate docs with doctype = name, else all types
                       Can use multiple times
  --exclude name    = Exclude doctype.  Pointless if --doctype used
                       Can use multiple times
  --noblocked       = Do not validate blocked documents
  --maxdocs number  = Stop after validating _number_ documents
  --progress number = Report progress to stderr every _number_ documents
                       Default = %d
  --outfile filename= Write messages to output file _filename_
                       Default = "%s" in CDR log directory
                       If --quiet, only summaries are logged
  --host name       = Name of host computer, else this computer
  --port number     = CDR server transaction port number, else uses default
""" % (RPT_COUNT, LOGFILE))
    sys.exit(1)

####################################################################
# Main program
####################################################################
# Initialize globals and settable options
valSchema = 'Y'
valLinks  = 'Y'
quiet     = False
verbose   = False
valOnly   = 'N'
inclType  = []
exclType  = []
noblocked = False
maxCount  = 999999999
progCount = RPT_COUNT
outFile   = LOGFILE
host      = cdr.DEFAULT_HOST
port      = cdr.DEFAULT_PORT
userid    = None
password  = None
log       = None
docTypeErrs = {}
docTypeCount = {}

# Parse command line
try:
    (opts, args) = getopt.getopt (sys.argv[1:], "", ('schemaonly', 'linkonly',
                    'quiet', 'verbose', 'noupdate', 'noblocked',
                    'include=', 'exclude=',
                    'maxdocs=', 'progress=', 'outfile=', 'host=', 'port='))
except getopt.GetoptError, info:
    usage ("Command line error: %s" % str(info))

# Read options, if any
argDisplay = ""
for (option, optarg) in opts:

    # Assemble args for logfile
    argDisplay += "   %s" % option
    if optarg:
        argDisplay += " %s" % optarg
    argDisplay += "\n"

    # Set options
    if option == '--schemaonly':
        valLinks = 'N'
    elif option == '--linkonly':
        valSchema = 'N'
    elif option == '--quiet':
        quiet = True
    elif option == '--verbose':
        verbose = True
    elif option == '--noupdate':
        valOnly = 'Y'
    elif option == '--include':
        inclType.append(optarg)
    elif option == '--exclude':
        exclType.append(optarg)
    elif option == '--noblocked':
        noblocked = True
    elif option == '--maxdocs':
        try:
            maxCount = int(optarg)
        except ValueError:
            usage ("option --maxdocs requires numeric argument")
    elif option == '--progress':
        try:
            progCount = int(optarg)
        except ValueError:
            usage ("option --progress requires numeric argument")
    elif option == '--outfile':
        outFile = optarg
    elif option == '--port':
        try:
            port = int(optarg)
        except ValueError:
            usage ("option --port requires numeric argument")
    elif option == '--host':
        host = optarg

# Read userid and password
if len(args) < 2:
    usage ("Missing userid and/or password")
if len(args) > 2:
    usage ("Extra argument(s) on command line")
userid   = args[0]
password = args[1]

# Login, verifying userid and password
session = cdr.login (userid, password, host=host, port=port)
if not session:
    usage ("Unable to login to %s (port %d) with userid and password" % \
           (host, port))

# Verify parms
if not valLinks and not valSchema:
    usage ("Can't turn off both schema and link validation")
if quiet and verbose:
    usage ("Can't select both --quiet and --verbose")
if quiet and valOnly == 'Y':
    usage ("Can't select both --quiet and --noupdate")


# Construct command to select all records to process
selCmd = "SELECT d.id, t.name FROM document d, doc_type t\n" \
         " WHERE d.doc_type = t.id\n"

# Specifically included doc types
if len(inclType) > 0:
    inList = ""
    for docType in inclType:
        if len(inList) > 0:
            inList += ','
        inList += "'%s'" % docType
    selCmd += " AND t.name IN (%s)\n" % inList

# Specifically excluded doc types
if len(exclType) > 0:
    for docType in exclType:
        selCmd += " AND t.name <> '%s'\n" % docType

# Active only
if noblocked:
    selCmd += " AND d.active_status <> 'I'\n"

# Presentation order
selCmd += " ORDER BY t.name, d.id\n"

# Open log
log = cdr.Log(LOGFILE, logTime=False, logPID=False)

# Report to log
log.write("Revalidating documents on host %s at %s" % (host, time.ctime()),
          stdout=True)
if argDisplay:
    log.write("\nArguments:")
    log.write(argDisplay)
log.write("\nUser = %s" % userid)
log.write("""
Selection query:
%s
""" % selCmd, stdout=True)

# Select everything
try:
    conn   = cdrdb.connect()
    cursor = conn.cursor()
    cursor.execute (selCmd)
    rows = cursor.fetchall()
except StandardError, info:
    sys.stderr.write ("Database error: %s\n" % str(info))
    sys.exit(1)
except Exception, info:
    sys.stderr.write ("Database exception: %s\n" % str(info))
    sys.exit(1)

# Report num docs we'll process
log.write("Selected %d documents" % len(rows), stdout=True)

####################################################################
# Main loop - Validate each selected document
####################################################################
valCount = 0
errCount = 0
lastType = None
for rowDocId, rowDocType in rows:

    # Quit if reached requested limit, could even be 0
    if valCount >= maxCount:
        break

    # Validate next document
    try:
        resp = cdr.valDoc (session, rowDocType, rowDocId,
                           valLinks = valLinks, valSchema = valSchema,
                           validateOnly = valOnly, host = host, port = port)
    except StandardError, info:
        log.write("Stopped on error, doctype %s doc=%d: %s" % \
                   (rowDocType, rowDocId, str(info)), stderr=True)
        sys.exit(1)
    except Exception, info:
        log.write("Stopped on exception, doctype %s doc=%d: %s" % \
                   (rowDocType, rowDocId, str(info)), stderr=True)
        sys.exit(1)

    # Initialize counters for new doctype
    if rowDocType != lastType:
        docTypeCount[rowDocType] = 0
        docTypeErrs[rowDocType] = 0
        lastType = rowDocType

    # Count number of docs of this type
    docTypeCount[rowDocType] += 1

    # Only look at response if we were not quieted
    if not quiet:
        # Were there errors?
        errMsgs = cdr.getErrors (resp, 0)
        if len(errMsgs):

            # Output info
            log.write("%s: %d:\n%s\n---" % (rowDocType, rowDocId, errMsgs))
            errCount += 1

            # Count by doc type
            if docTypeErrs.has_key(rowDocType):
                docTypeErrs[rowDocType] += 1

        elif verbose:
            # Only output good records if in verbose mode
            log.write("%s: %d:\n" % (rowDocType, rowDocId))

    # Record and report progress, not written to log file
    valCount += 1
    if valCount % progCount == 0:
        sys.stderr.write ("Validated %d docs\n" % valCount)

# Done processing, add final stats
docTypesReport = """
Errors by document type:
    Docs   Errs Document type
  ====== ====== ==================
"""
listDocTypes  = docTypeErrs.keys()
listDocTypes.sort()
for docType in listDocTypes:
    docTypesReport += "  %6d %6d %s\n" % \
         (docTypeCount[docType], docTypeErrs[docType], docType)

log.write("""
==========
Final Totals:
  %6d documents validated
  %6d with errors
%s""" % (valCount, errCount, docTypesReport))
