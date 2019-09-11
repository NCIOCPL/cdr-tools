#!/usr/bin/env python
#----------------------------------------------------------------------
#
# Extracts command sets from the CDR command log into a form which can
# be resubmitted to the CDR Server.
#
# Attributes are inserted into each CdrCommandSet element for the
# ID of the thread used to process the commands and for the date/time
# when the commands were originally submitted.
#
# An optional command-line argument can be given to specify that only
# commands submitted by the CdrGuest account are to be extracted (these
# are the most likely commands to succeed on resubmission).
#
# See the more extensive comments in RunCdrCommands.py
#
#----------------------------------------------------------------------
import cdrdb, re, sys, time

#----------------------------------------------------------------------
# Explain how to invoke the program.
#----------------------------------------------------------------------
def usage():
    for line in (
        'usage: GetCdrCommands [--guestonly] start-time [end-time]\n',
        ' e.g.: GetCdrCommands "2002-09-28 13:51" "2002-09-28 13:55"\n'
    ):
        sys.stderr.write(line)

#----------------------------------------------------------------------
# Parse the command-line arguments.
#----------------------------------------------------------------------
nextArg = 1
guestOnly = False
useArchive = False
while len(sys.argv) > nextArg and sys.argv[nextArg] in ("--guestonly",
                                                        "--archives"):
    if sys.argv[nextArg] == "--guestonly":
        guestOnly = True
    else:
        useArchive = True
    nextArg += 1
if len(sys.argv) <= nextArg:
    usage()
    sys.exit(1)
startTime = sys.argv[nextArg]
nextArg += 1
if len(sys.argv) > nextArg:
    endTime = sys.argv[nextArg]
    nextArg += 1
else:
    endTime = time.strftime("%Y-%m-%d %H:%M:%S")

#----------------------------------------------------------------------
# Callback for regular-expression substitution to insert attributes.
#----------------------------------------------------------------------
pattern = re.compile("<CdrCommandSet>")
def insertAttrs(matchobj):
    return "<CdrCommandSet thread='%d' received='%s'>" % (thread, received)

#----------------------------------------------------------------------
# Take care of characters that print can't handle.
#----------------------------------------------------------------------
decodePattern = re.compile(u"([\u0080-\uffff])")
def decode(xml):
    return re.sub(decodePattern,
                  lambda match: u"&#x%X;" % ord(match.group(0)[0]), xml)
#                  unicode(xml, 'utf-8')).encode('latin-1')

#----------------------------------------------------------------------
# Get the rows from the command log.
#----------------------------------------------------------------------
if useArchive:
    db = 'cdrArchive'
    table = 'command_log_history'
else:
    db = 'cdr'
    table = 'command_log'
sys.stderr.write("db=%s startTime=%s endTime=%s guestOnly=%s\n" %
                 (db, startTime, endTime, guestOnly))
conn = cdrdb.connect(db = db)
cursor = conn.cursor()
cursor.execute("""\
        SELECT command, thread, received
          FROM %s
         WHERE received BETWEEN '%s' AND '%s'
      ORDER BY received""" % (table, startTime, endTime))
row = cursor.fetchone()

#----------------------------------------------------------------------
# Top-level wrapper element.
#----------------------------------------------------------------------
print("<CdrCommandSets>")

#----------------------------------------------------------------------
# Add each set of commands, filtering if requested.
#----------------------------------------------------------------------
while row:
    commandSet, thread, received = row
    if not guestOnly or commandSet.find("<SessionId>guest</SessionId>") != -1:
        commandSet = pattern.sub(insertAttrs, commandSet)
        print(decode(commandSet))
    row = cursor.fetchone()

#----------------------------------------------------------------------
# Close top-level wrapper element.
#----------------------------------------------------------------------
print("</CdrCommandSets>")
