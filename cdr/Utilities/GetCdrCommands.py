#----------------------------------------------------------------------
#
# $Id: GetCdrCommands.py,v 1.1 2002-09-29 14:15:21 bkline Exp $
#
# Extracts command sets from the CDR command log into a form which can
# be resubmitted to the CDR Server.
#
# See the more extensive comments in RunCdrCommands.py
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdrdb, re, sys

if len(sys.argv) < 2:
    sys.stderr.write("usage: GetCommands2 start-time [end-time]\n")
    sys.stderr.write(
            ' e.g.: GetCommands2 "2002-09-28 13:51" "2002-09-28 13:55"\n')
    sys.exit(1)
startTime = sys.argv[1]

# Warning! Y2.2K bug.
endTime   = len(sys.argv) < 3 and "2200-01-01" or sys.argv[2]
def insertAttrs(matchobj):
    return "<CdrCommandSet thread='%d' received='%s'>" % (thread, received)

pattern = re.compile("<CdrCommandSet>")
conn = cdrdb.connect()
cursor = conn.cursor()
cursor.execute("""\
        SELECT command, thread, received
          FROM command_log
         WHERE received BETWEEN '%s' AND '%s'
      ORDER BY received""" % (startTime, endTime))
row = cursor.fetchone()
print "<CdrCommandSets>"
while row:
    commandSet, thread, received = row
    commandSet = pattern.sub(insertAttrs, commandSet)
    print commandSet
    row = cursor.fetchone()
print "</CdrCommandSets>"
