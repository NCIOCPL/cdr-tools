#----------------------------------------------------------------------
#
# Illustrates invocation of a stored procedure to obtain the last results
# set when the number of results sets is unknown.  Assumes that no interim
# results sets (nor the final results set, for that matter) will be so
# prohibitively large that keeping the entire set in memory is an unacceptable
# option.
#
# New example program for Alan.
#
#----------------------------------------------------------------------
import cdrdb
import datetime
import sys

def getLastResultsSet(cursor, procName, parms):
    cursor.callproc(procName, parms, timeout = 300)
    lastSet = []
    done = False
    while not done:
        if cursor.description:
            lastSet = cursor.fetchall()
        if not cursor.nextset():
            done = True
    return lastSet

cursor = cdrdb.connect().cursor()

# ADO/DB is picky about parameter types; can't use a string here!
if len(sys.argv) > 1:
    try:
        parm = datetime.datetime.strptime(sys.argv[1], "%Y-%m-%d")
    except:
        print("usage: python CallProcDemo.py [YYYY-MM-DD]")
else:
    parm= datetime.datetime.today() - datetime.timedelta(2)
print(getLastResultsSet(cursor, "cdr_changed_docs", (parm,)))
