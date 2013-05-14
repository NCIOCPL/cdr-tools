#----------------------------------------------------------------------
#
# $Id$
#
# Concatenate output of diff files for quick review of test mode
# global change runs.
#
#                                       Alan Meyer
#                                       May, 2011
#----------------------------------------------------------------------
import sys, os, re

FPAT = re.compile("(?P<cdrid>CDR\d{10})\.(?P<ver>[a-z]{3,5})\.diff")

def usage(msg=None):
    """
    Display optional error message plus usage info.  Then exit.
    """
    if msg:
        sys.stderr.write("%s\n\n" % msg)

    sys.stderr.write("""
usage: DiffReport.py docver {docver} {docver}
  Read all the diff reports in a test mode global change output directory
  and catenate difference files as a summary to stdout of all changes
  that occurred.

  Run this program in the directory that holds the output files.

  Parameters:
    docver = One or more of:
      "cwd"   = Current working doc changes
      "pub"   = Last publishable version changes
      "lastv" = Last non-publishable version changes

  Some versions may not appear if they are the same as others, e.g., if cwd,
  lastv and pub are all the same version then only cwd will appear even if
  all three have been specified.
""")
if len(sys.argv) < 2:
    usage("Insufficient arguments")

# Get parameters
versions = []
for parm in sys.argv[1:]:
    if parm not in ("cwd", "pub", "lastv"):
        usage('Unrecognized parameter: "%s"' % parm)
    versions.append(parm)

lastCdrId = ""


# Examine all files in the directory
fnames = os.listdir(".")
for f in fnames:
    m = FPAT.match(f)
    if m:
        cdrId = m.group("cdrid")
        ver   = m.group("ver")

        # Only show CDR ID once, with blank line separator
        if cdrId != lastCdrId:
            lastCdrId = cdrId
            print("\n%s:" % cdrId)
            print("=====================================================")

        # Is it a version we want?
        if ver not in versions:
            continue

        # What we're showing
        print("\n____ %s ____" % ver)

        # Copy out the contents of the diff
        fp = open(f)
        text = fp.read()
        print(text)
        fp.close()

