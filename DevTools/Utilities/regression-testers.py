"""
Restore permissions for Regression Testers group after db refresh from PROD
"""

from cdrapi import db

conn = db.connect()
cursor = conn.cursor()
ACTIONS = (
    ("ADD DOCUMENT", "Person"),
    ("ADD DOCUMENT", "Filter"),
    ("ADD DOCUMENT", "schema"),
    ("ADD DOCUMENT", "Summary"),
    ("ADD DOCUMENT", "Mailer"),
    ("ADD DOCUMENT", "xxtest"),
    ("MODIFY DOCUMENT", "Person"),
    ("MODIFY DOCUMENT", "Filter"),
    ("MODIFY DOCUMENT", "schema"),
    ("MODIFY DOCUMENT", "Summary"),
    ("MODIFY DOCUMENT", "Mailer"),
    ("MODIFY DOCUMENT", "xxtest"),
    ("DELETE DOCUMENT", "Person"),
    ("DELETE DOCUMENT", "Filter"),
    ("DELETE DOCUMENT", "schema"),
    ("DELETE DOCUMENT", "Summary"),
    ("DELETE DOCUMENT", "Mailer"),
    ("DELETE DOCUMENT", "xxtest"),
    ("PUBLISH DOCUMENT", "xxtest"),
    ("CREATE USER", ""),
    ("DELETE USER", ""),
    ("MODIFY USER", ""),
    ("ADD GROUP", ""),
    ("MODIFY GROUP", ""),
    ("DELETE GROUP", ""),
    ("GET GROUP", ""),
    ("LIST GROUPS", ""),
    ("GET USER", ""),
    ("LIST USERS", ""),
    ("VALIDATE DOCUMENT", "Person"),
    ("VALIDATE DOCUMENT", "Filter"),
    ("VALIDATE DOCUMENT", "Summary"),
    ("VALIDATE DOCUMENT", "Mailer"),
    ("VALIDATE DOCUMENT", "xxtest"),
    ("FILTER DOCUMENT", "Person"),
    ("FILTER DOCUMENT", "schema"),
    ("FILTER DOCUMENT", "Summary"),
    ("FILTER DOCUMENT", "xxtest"),
    ("LIST DOCTYPES", ""),
    ("FORCE CHECKIN", "Person"),
    ("FORCE CHECKIN", "schema"),
    ("FORCE CHECKIN", "Mailer"),
    ("FORCE CHECKIN", "xxtest"),
    ("FORCE CHECKOUT", "Person"),
    ("FORCE CHECKOUT", "schema"),
    ("FORCE CHECKOUT", "Mailer"),
    ("FORCE CHECKOUT", "xxtest"),
    ("GET SCHEMA", "Person"),
    ("GET SCHEMA", "Mailer"),
    ("GET SCHEMA", "xxtest"),
    ("GET DOCTYPE", "Person"),
    ("GET DOCTYPE", "Filter"),
    ("GET DOCTYPE", "Mailer"),
    ("GET DOCTYPE", "xxtest"),
    ("ADD DOCTYPE", ""),
    ("MODIFY DOCTYPE", "Person"),
    ("MODIFY DOCTYPE", "xxtest"),
    ("DELETE DOCTYPE", ""),
    ("GET TREE", ""),
    ("LIST ACTIONS", ""),
    ("GET ACTION", ""),
    ("MODIFY ACTION", ""),
    ("DELETE ACTION", ""),
    ("ADD LINKTYPE", ""),
    ("MODIFY LINKTYPE", ""),
    ("DELETE LINKTYPE", ""),
    ("LIST LINKTYPES", ""),
    ("GET LINKTYPE", ""),
    ("ADD QUERY TERM DEF", ""),
    ("DELETE QUERY TERM DEF", ""),
    ("SUMMARY MAILERS", ""),
    ("RECEIVE MAILER REPORTS", "Person"),
    ("UNLOCK", ""),
    ("MAKE GLOBAL CHANGES", "xxtest"),
    ("ADD FILTER SET", ""),
    ("DELETE FILTER SET", ""),
    ("MODIFY FILTER SET", ""),
    ("SET_SYS_VALUE", ""),
    ("EDIT GLOSSARY MAP", ""),
    ("ADD ACTION", ""),
    ("REPLACE CWD WITH VERSION", ""),
    ("BLOCK DOCUMENT", ""),
    ("UNBLOCK DOCUMENT", ""),
    ("USE PUBLISHING SYSTEM", ""),
    ("UPLOAD ZIP CODES", ""),
    ("GET SYS CONFIG", ""),
    ("RUN LONG REPORT", "")
)

cursor.execute("SELECT id FROM grp WHERE name = 'Regression Testers'")
row = cursor.fetchone()
if not row:
    raise Exception("Regression Testers group not found")
group = row.id
actions = {}
doctypes = {}
for action_name, doctype_name in ACTIONS:
    if action_name not in actions:
        cursor.execute("SELECT id FROM action WHERE name = ?", (action_name,))
        row = cursor.fetchone()
        if row:
            actions[action_name] = row.id
        else:
            actions[action_name] = None
            print(("skipping unknown action {!r}".format(action_name)))
    if doctype_name not in doctypes:
        cursor.execute("SELECT id FROM doc_type WHERE name = ?",
                       (doctype_name,))
        row = cursor.fetchone()
        if row:
            doctypes[doctype_name] = row.id
        else:
            doctypes[doctype_name] = None
            print(("skipping unknown doctype {!r}".format(doctype_name)))
    action = actions[action_name]
    doctype = doctypes[doctype_name]
    if action is not None and doctype is not None:
        if doctype_name:
            print(f"Granting {action_name} on {doctype_name} documents")
        else:
            print(f"Granting {action_name}")
        cursor.execute(f"""\
            INSERT INTO grp_action (grp, action, doc_type)
            SELECT {group:d}, {action:d}, {doctype:d}
            WHERE NOT EXISTS (
                SELECT 1
                  FROM grp_action
                 WHERE grp = {group:d}
                   AND action = {action:d}
                   AND doc_type = {doctype:d});""")
conn.commit()
