#----------------------------------------------------------------------
#
# $Id$
#
# Create a temporary CDR login for migrating documents from Bach
# to Franck for testing of nightly publishing, and wipe out the
# permissions for adding, modifying, or deleting documents from
# all other CDR accounts on Franck, so users can't inadvertently
# invalidate the testing conditions.  Saves suppressed group
# memberships in the table xgrp_action (if this table exists
# before the program is run the program will abort; this approach
# is taken instead of wiping out the table first to prevent
# inadvertent loss of the original group membership information).
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdrdb, cdr, sys

# Check for required command-line arguments.
if len(sys.argv) != 3:
    print "usage: SuppressDocSaves.py cdr-uid cdr-pwd"
    sys.exit(1)
uid, pwd = sys.argv[1:]

# Connect to the CDR database.
conn = cdrdb.connect()
cursor = conn.cursor()

# Save the permissions we're about to suppress (so we can restore them
# if necessary).
cursor.execute("""\
    SELECT *
      INTO xgrp_action
      FROM grp_action
     WHERE action IN (SELECT DISTINCT action
                                 FROM audit_trail)""")
conn.commit()

# Wipe out all of the permissions for auditable actions.
cursor.execute("""\
    DELETE FROM grp_action
          WHERE action IN (SELECT DISTINCT action
                                      FROM audit_trail)""")
conn.commit()

# Create a new group.
actions = {}
cursor.execute("""\
    SELECT DISTINCT d.name, a.name
               FROM xgrp_action x
               JOIN doc_type d
                 ON d.id = x.doc_type
               JOIN action a
                 ON a.id = x.action""")
for docType, action in cursor.fetchall():
    if action not in actions:
        actions[action] = []
    if docType:
        actions[action].append(docType)
group = cdr.Group('NightlyRefreshFromProdGroup', actions, None,
                  "Temporary group for testing nightly publishing")
session = cdr.login(sys.argv[1], sys.argv[2])
errors = cdr.putGroup(session, None, group)
if errors:
    print errors
    cdr.logout(session)
    sys.exit(1)

# Create the new user account and put it in the new group.
user = cdr.User('NightlyRefreshFromProd', 'PhazUvTheM00n',
                groups = [group.name],
                comment = 'Temporary user for testing nightly publishing')
errors = cdr.putUser(session, None, user)
cdr.logout(session)
