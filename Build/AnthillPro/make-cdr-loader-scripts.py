#----------------------------------------------------------------------
#
# $Id$
#
# Used to generate CdrLoader shell scripts.  Takes the name of the
# CDR client program as the only command-line argument.  Run this
# in d:\cdr\ClientFiles.  For example:
#
# make-cdr-loader-scripts CdrClient20120915-0839.exe
#
#----------------------------------------------------------------------
import sys

exe = sys.argv[1]

# Main launcher.
fp = open("CDRLoader.cmd", "w")
fp.write("set OAPERUSERTLIBREG=1\n")
fp.write("%s\n" % exe)
fp.close()

# Re-launcher (when we have to replace the program)
fp = open("CdrRunAgain.cmd", "w")
fp.write("set OAPERUSERTLIBREG=1\n")
fp.write("%s --run-again\n" % exe)
fp.close()

# Elevated debugging levels
fp = open("CdrClientDebug2.cmd", "w")
fp.write("set OAPERUSERTLIBREG=1\n")
fp.write("set CDR_CLIENT_DEBUG_LEVEL=2\n")
fp.write("set CDR_SERVER_DEBUG_LEVEL=2\n")
fp.write("%s\n" % exe)
fp.close()

# Highest debugging levels
fp = open("CdrClientDebug3.cmd", "w")
fp.write("set OAPERUSERTLIBREG=1\n")
fp.write("set CDR_CLIENT_DEBUG_LEVEL=3\n")
fp.write("set CDR_SERVER_DEBUG_LEVEL=3\n")
fp.write("%s\n" % exe)
fp.close()
