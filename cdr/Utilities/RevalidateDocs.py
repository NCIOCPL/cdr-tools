"""
    Validate some or all documents in the database.

    See usage() for parameters.
"""

import sys, getopt, cdr, cdrdb

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
  --doctype name    = Only validate docs with doctype = name, else all types
  --maxdocs number  = Stop after validating _number_ documents
  --outfile filename= Write messages to output file _filename_
                       If --quiet, --outfile is illegal
  --host name       = Name of host computer, else this computer
  --port number     = CDR server transaction port number, else uses default
""")
    sys.exit(1)

####################################################################
# Main program
####################################################################
# Set default values for settable options
valSchema = 'Y'
valLinks  = 'Y'
quiet     = 0
verbose   = 0
valOnly   = 'N'
docType   = None
maxCount  = 999999999
outFile   = None
host      = cdr.DEFAULT_HOST
port      = cdr.DEFAULT_PORT
userid    = None
password  = None

# Parse command line
try:
    (opts, args) = getopt.getopt (sys.argv[1:], "", ('schemaonly', 'linkonly',
                    'quiet', 'verbose', 'noupdate',
                    'doctype=', 'maxdocs=', 'outfile=',
                    'host=', 'port='))
except getopt.GetoptError, info:
    usage ("Command line error: %s" % str(info))

# Read options, if any
for (option, optarg) in opts:

    if option == '--schemaonly':
        valLinks = 'N'
    elif option == '--linkonly':
        valSchema = 'N'
    elif option == '--quiet':
        quiet = 1
    elif option == '--verbose':
        verbose = 1
    elif option == '--noupdate':
        valOnly = 'Y'
    elif option == '--doctype':
        if docType:
            usage ("Sorry, can't specify more than one doctype arg")
        docType = optarg
    elif option == '--maxdocs':
        try:
            maxCount = int(optarg)
        except ValueError:
            usage ("option --maxdocs requires numeric argument")
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
if outFile and quiet:
    usage ("If --quiet selected, --outfile is illegal")
if quiet and verbose:
    usage ("Can't select both --quiet and --verbose")
if quiet and valOnly == 'Y':
    usage ("Can't select both --quiet and --noupdate")

# Construct command to select all records to process
selCmd = "SELECT d.id, t.name FROM document d, doc_type t " \
         " WHERE d.doc_type = t.id"
if docType:
    selCmd += " AND t.name = '%s'" % docType

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

# Okay so far, setup output file, if requested
outf = None
if not quiet:
    if outFile:
        try:
            outf = open (outFile, "w")
        except IOError, info:
            usage ("Unable to open: %s" % str(info))
    else:
        outf = sys.stdout


####################################################################
# Main loop - Validate each selected document
####################################################################
valCount = 0
errCount = 0
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
        sys.stderr.write ("Stopped on error, doctype %s doc=%d: %s" % \
                          (rowDocType, rowDocId, str(info)))
        sys.exit(1)
    except Exception, info:
        sys.stderr.write ("Stopped on exception, doctype %s doc=%d: %s" % \
                          (rowDocType, rowDocId, str(info)))
        sys.exit(1)

    valCount += 1

    # Only look at response if we were not quieted
    if not quiet:
        # Were there errors?
        errMsgs = cdr.getErrors (resp, 0)
        if len(errMsgs):

            # Output info
            outf.write ("%s: %d:\n%s\n---\n" % (rowDocType, rowDocId, errMsgs))

            errCount += 1

        elif verbose:
            # Only output good records if in verbose mode
            outf.write ("%s: %d:\n" % (rowDocType, rowDocId))

# Done processing, add final stats if requested
if not quiet:
    outf.write ("""
==========
Final Totals:
    %d documents validated
    %d with errors
""" % (valCount, errCount))

# Cleanup
if outFile:
    outf.close()
