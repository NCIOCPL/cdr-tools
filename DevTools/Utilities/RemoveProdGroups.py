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
import argparse
import getpass
import cdr, sys

LOGFILE = "RemoveProdGroups.log"
LOGLEVEL = 1

def create_parser():
    """
    Create the object which collects the run-time arguments.
    """

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""\
This program needs to be run on the lower tiers after database refresh.
Since the DB is refreshed with the data from PROD the script will update 
the email notification groups and remove all users.""")
    parser.add_argument("--runmode", "-r", choices=['live', 'test'], 
                                           required=True)
    parser.add_argument("--tier", "-t", choices=['PROD','STAGE','QA','DEV'])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--session", "-s")
    group.add_argument("--user", "-u")
    return parser

# ---------------------------------------------------------------------
# Function to update the groups membership
# ---------------------------------------------------------------------
def updateGroups(session, testMode, tier):
    test = testMode

    # Groups to be reset
    # ------------------
    groups  = {"BatchCTGovMapping Notification":  ['volker'],
               "CTGov Duplicate Notification":    ['volker'],
               "CTGov Export Notification":       ['bkline', 'volker'],
               "CTGov Link Fix Notification":     ['bkline', 'volker'],
               "GovDelivery ES Docs Notification":['operator', 'volker'],
               "GovDelivery EN Docs Notification":['operator', 'volker'],
               "Hotfix Remove Notification":      ['operator', 'volker'],
               "ICRDB Statistics Notification":   ['operator', 'volker'],
               "Licensee Report Notification":    ['operator', 'volker'],
               "Nightly Publishing Notification": ['operator', 'volker'],
               "Operator Publishing Notification":['operator', 'volker'],
               "Test Group Dada":                 ['volker'],
               "Test Publishing Notification":    ['operator', 'volker'],
               "VOL Notification":                ['operator', 'volker'],
               "Weekly Publishing Notification":  ['operator', 'volker']
               }

    ierror = 0
    for group_name in groups:
        try:
            group = cdr.getGroup(session, group_name, tier=tier)
        except:
            # If the group doesn't exist on this tier continue
            # ------------------------------------------------
            ierror += 1
            l.write("***** ERROR *****", stdout = True)
            l.write("Group not available on this tier!!!", 
                                         stdout = True)
            l.write(group_name,          stdout = True)
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
            error = cdr.putGroup(session, group_name, group, tier=tier)
            l.write("%s: %s" % (group_name, error or "saved"), stdout = True)
        l.write("----", stdout = True)

    return ierror

# -----------------------------------------------------------------
# Main program starts here
# -----------------------------------------------------------------
if __name__ == "__main__":

    # Parse command-line options and arguments
    # ----------------------------------------
    parser = create_parser()
    opts = parser.parse_args()

    # Open Log file and enter start message
    # -------------------------------------
    l = cdr.Log(LOGFILE)
    l.write('RemoveProdGroups - Started', stdout = True)
    # l.write('Arguments: %s' % opts, stdout=True)

    # Live or test mode
    # -----------------
    if opts.runmode == "test":
        testMode = True
    else:
        testMode = False

    tier = opts.tier

    # Log into the CDR on the target server.
    # --------------------------------------
    if opts.session:
        session = opts.session
    else:
        password = getpass.getpass()
        session = cdr.login(opts.user, password, tier=opts.tier)
        error_message = cdr.checkErr(session)
        if error_message:
            parser.error(error_message)

    error_count = updateGroups(session, testMode, tier)

    l.write('RemoveProdGroups - Finished', stdout = True)
    l.write('Missing groups: %d' % error_count, stdout = True)
    sys.exit(0)
