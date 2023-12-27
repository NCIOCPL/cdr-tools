#!/usr/bin/env python3
# ----------------------------------------------------------------------
#
# After a DB refresh all of the PROD group notifications apply to all
# of the lower tiers.  We don't really want to send out notification
# emails to users from the lower tiers.
# This script restores the default distribution list to the lower tier
# after a DB refresh has been performed.
#
# ----------------------------------------------------------------------
import argparse
import getpass
import sys
import cdr
import json

TIERS = "PROD", "STAGE", "QA", "DEV"


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
    parser.add_argument("--tier", "-t", choices=TIERS)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--session", "-s")
    group.add_argument("--user", "-u")
    return parser


# ---------------------------------------------------------------------
# Function to update the groups membership
# ---------------------------------------------------------------------
def updateGroups(session, testing, tier):

    # Groups to be reset are stored in the control table
    # --------------------------------------------------
    getGroups = cdr.getControlValue("DBRefresh", "RemoveProdGroups", tier=tier)
    print("Groups stored in Control Table")
    print("==============================")
    print(getGroups)
    print()
    groups = json.loads(getGroups)
    allGroups = cdr.getGroups(session, tier=tier)

    ierror = 0
    for group_name in groups:
        try:
            group = cdr.getGroup(session, group_name, tier=tier)
        except Exception:
            # If the group doesn't exist on this tier continue
            # ------------------------------------------------
            ierror += 1
            logger.error("***** ERROR *****")
            logger.error("Group not available on this tier!!!")
            logger.error(group_name)
            logger.error("***** ERROR *****")
            continue

        logger.info("Group Name: %s", group_name)
        logger.info("Member(s):")
        logger.info("   Old: %s", group.users)
        group.users = groups[group_name]
        group.users.sort()
        logger.info("   New: %s", group.users)

        if testing:
            logger.info("TESTMODE:  No update")
        else:
            try:
                cdr.putGroup(session, group_name, group, tier=tier)
                logger.info("%s: saved", group_name)
            except Exception as e:
                logger.error("%s: %s", group_name, e)
        logger.info("----")

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
    logger = cdr.Logging.get_logger("RemoveProdGroups", console=True)
    logger.info('RemoveProdGroups - Started')
    logger.debug('Arguments: %s', opts)

    # Live or test mode
    # -----------------
    testing = opts.runmode == "test"

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

    error_count = updateGroups(session, testing, opts.tier)

    logger.info('RemoveProdGroups - Finished')
    logger.info('Missing groups: %d', error_count)
    sys.exit(0)
