#!/usr/bin/env python
#----------------------------------------------------------------------
#
# After a DB refresh all of the PROD group notifications apply to all
# of the lower tiers.  We don't really want to send out notification
# emails to users from the lower tiers.
# This script restores the default distribution list to the lower tier
# after a DB refresh has been performed.
#
#----------------------------------------------------------------------
import cdr, sys

LOGFILE = "RemoveProdGroups.log"
LOGLEVEL = 1

# ---------------------------------------------------------------------
# Function to update the groups membership
# ---------------------------------------------------------------------
def updateGroups(uid, pwd, testMode):
    test = testMode
    session = cdr.login(uid, pwd)

    # Groups to be reset
    # ------------------
    groups  = {"BatchCTGovMapping Notification":  ['volker'],
               "CTGov Duplicate Notification":    ['volker'],
               "CTGov Export Notification":       ['bkline', 'volker'],
               "CTGov Link Fix Notification":     ['bkline', 'volker'],
               "CTRPDownload Notification":       ['bkline', 'volker'],
               "Hotfix Remove Notification":      ['operator', 'volker'],
               "ICRDB Statistics Notification":   ['operator', 'volker'],
               "Licensee Report Notification":    ['operator', 'volker'],
               "Nightly Publishing Notification": ['operator', 'volker'],
               "Operator Publishing Notification":['operator', 'volker'],
               "Test Publishing Notification":    ['operator', 'volker'],
               "VOL Notification":                ['operator', 'volker'],
               "Test Group Dada": ['volker'],
               "Weekly Publishing Notification":  ['operator', 'volker']}

    for group_name in groups:
        group = cdr.getGroup(session, group_name)

        # If the group doesn't exist on this tier continue
        # ------------------------------------------------
        if (type(group) == type("")):
            l.write("***** ERROR *****", stdout = True)
            l.write(group, stdout = True)
            l.write("***** ERROR *****", stdout = True)
            continue

        l.write("Group Name: %s" % group_name, stdout = True)
        l.write("Member(s): ",                 stdout = True)
        l.write("   Old: %s" % group.users,    stdout = True)
        group.users = groups[group_name]
        group.users.sort()
        l.write("   New: %s" % group.users,    stdout = True)

        error = ''
        if testMode:
            l.write("TESTMODE:  No update", stdout = True)
        else:
            error = cdr.putGroup(session, group_name, group)
            l.write("%s: %s" % (group_name, error or "saved"), stdout = True)
        l.write("----", stdout = True)

    return

# -----------------------------------------------------------------
# Main program starts here
# -----------------------------------------------------------------
if __name__ == "__main__":

    # Open Log file and enter start message
    # -------------------------------------
    l = cdr.Log(LOGFILE)
    l.write('RemoveProdGroups - Started', stdout = True)
    l.write('Arguments: %s' % sys.argv, stdout=True)

    if len(sys.argv) != 4:
        l.write("usage: RemoveProdGroups.py userId pw live|test")
        sys.stderr.write("usage: RemoveProdGroups.py userId pw live|test\n")
        sys.exit(1)

    # Get args
    # --------
    uid, pwd, runMode = sys.argv[1:]

    # Live or test mode
    # -----------------
    if runMode not in ("live", "test"):
        sys.stderr.write('Specify "live" or "test" for run mode\n')
        sys.exit(1)

    if runMode == "test":
        testMode = True
    else:
        testMode = False

    updateGroups(uid, pwd, testMode)

    l.write('RemoveProdGroups - Finished', stdout = True)
    sys.exit(0)
