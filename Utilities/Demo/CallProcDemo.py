#----------------------------------------------------------------------
#
# $Id$
#
# Illustrates invocation of a stored procedure to obtain the last results
# set when the number of results sets is unknown.  Assumes that no interim
# results sets (nor the final results set, for that matter) will be so
# prohibitively large that keeping the entire set in memory is an unacceptable
# option.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2009/01/27 19:29:50  bkline
# New example program for Alan.
#
#----------------------------------------------------------------------
import cdrdb

def getLastResultsSet(cursor, procName, parms):
    #cursor.execute(procName, parms, timeout = 300)
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
#print getLastResultsSet(cursor, "EXEC select_changed_non_active_protocols", [])
parms = []
print getLastResultsSet(cursor, "select_changed_non_active_protocols", parms)
