from cdrapi import db

conn = db.connect()
cursor = conn.cursor()
ACTIONS = (
    (u"ADD DOCUMENT", u"Person"),
    (u"ADD DOCUMENT", u"Filter"),
    (u"ADD DOCUMENT", u"schema"),
    (u"ADD DOCUMENT", u"Summary"),
    (u"ADD DOCUMENT", u"Mailer"),
    (u"ADD DOCUMENT", u"xxtest"),
    (u"MODIFY DOCUMENT", u"Person"),
    (u"MODIFY DOCUMENT", u"Filter"),
    (u"MODIFY DOCUMENT", u"schema"),
    (u"MODIFY DOCUMENT", u"Summary"),
    (u"MODIFY DOCUMENT", u"Mailer"),
    (u"MODIFY DOCUMENT", u"xxtest"),
    (u"DELETE DOCUMENT", u"Person"),
    (u"DELETE DOCUMENT", u"Filter"),
    (u"DELETE DOCUMENT", u"schema"),
    (u"DELETE DOCUMENT", u"Summary"),
    (u"DELETE DOCUMENT", u"Mailer"),
    (u"DELETE DOCUMENT", u"xxtest"),
    (u"PUBLISH DOCUMENT", u"xxtest"),
    (u"CREATE USER", u""),
    (u"DELETE USER", u""),
    (u"MODIFY USER", u""),
    (u"ADD GROUP", u""),
    (u"MODIFY GROUP", u""),
    (u"DELETE GROUP", u""),
    (u"GET GROUP", u""),
    (u"LIST GROUPS", u""),
    (u"GET USER", u""),
    (u"LIST USERS", u""),
    (u"VALIDATE DOCUMENT", u"Person"),
    (u"VALIDATE DOCUMENT", u"Filter"),
    (u"VALIDATE DOCUMENT", u"Summary"),
    (u"VALIDATE DOCUMENT", u"Mailer"),
    (u"VALIDATE DOCUMENT", u"xxtest"),
    (u"FILTER DOCUMENT", u"Person"),
    (u"FILTER DOCUMENT", u"schema"),
    (u"FILTER DOCUMENT", u"Summary"),
    (u"FILTER DOCUMENT", u"xxtest"),
    (u"LIST DOCTYPES", u""),
    (u"FORCE CHECKIN", u"Person"),
    (u"FORCE CHECKIN", u"schema"),
    (u"FORCE CHECKIN", u"Mailer"),
    (u"FORCE CHECKIN", u"xxtest"),
    (u"FORCE CHECKOUT", u"Person"),
    (u"FORCE CHECKOUT", u"schema"),
    (u"FORCE CHECKOUT", u"Mailer"),
    (u"FORCE CHECKOUT", u"xxtest"),
    (u"GET SCHEMA", u"Person"),
    (u"GET SCHEMA", u"Mailer"),
    (u"GET SCHEMA", u"xxtest"),
    (u"GET DOCTYPE", u"Person"),
    (u"GET DOCTYPE", u"Filter"),
    (u"GET DOCTYPE", u"Mailer"),
    (u"GET DOCTYPE", u"xxtest"),
    (u"ADD DOCTYPE", u""),
    (u"MODIFY DOCTYPE", u"Person"),
    (u"MODIFY DOCTYPE", u"xxtest"),
    (u"DELETE DOCTYPE", u""),
    (u"GET TREE", u""),
    (u"LIST ACTIONS", u""),
    (u"GET ACTION", u""),
    (u"MODIFY ACTION", u""),
    (u"DELETE ACTION", u""),
    (u"ADD LINKTYPE", u""),
    (u"MODIFY LINKTYPE", u""),
    (u"DELETE LINKTYPE", u""),
    (u"LIST LINKTYPES", u""),
    (u"GET LINKTYPE", u""),
    (u"ADD QUERY TERM DEF", u""),
    (u"DELETE QUERY TERM DEF", u""),
    (u"SUMMARY MAILERS", u""),
    (u"RECEIVE MAILER REPORTS", u"Person"),
    (u"UNLOCK", u""),
    (u"MAKE GLOBAL CHANGES", u"xxtest"),
    (u"ADD FILTER SET", u""),
    (u"DELETE FILTER SET", u""),
    (u"MODIFY FILTER SET", u""),
    (u"SET_SYS_VALUE", u""),
    (u"EDIT GLOSSARY MAP", u""),
    (u"EDIT RSS MAP", u""),
    (u"ADD ACTION", u""),
    (u"GP MAILERS", u""),
    (u"REPORT CTGOV ORPHANS", u""),
    (u"REPLACE CWD WITH VERSION", u""),
    (u"BLOCK DOCUMENT", u""),
    (u"UNBLOCK DOCUMENT", u""),
    (u"USE PUBLISHING SYSTEM", u""),
    (u"UPLOAD ZIP CODES", u""),
    (u"GET SYS CONFIG", u""),
    (u"RUN LONG REPORT", u"")
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
            print("skipping unknown action {!r}".format(action_name))
    if doctype_name not in doctypes:
        cursor.execute("SELECT id FROM doc_type WHERE name = ?",
                       (doctype_name,))
        row = cursor.fetchone()
        if row:
            doctypes[doctype_name] = row.id
        else:
            doctypes[doctype_name] = None
            print("skipping unknown doctype {!r}".format(doctype_name))
    action = actions[action_name]
    doctype = doctypes[doctype_name]
    if action is not None and doctype is not None:
        args = (group, action, doctype) * 2
        if doctype_name:
            print("Granting {} on {} documents".format(action_name,
                                                       doctype_name))
        else:
            print("Granting {}".format(action_name))
        cursor.execute("""\
            INSERT INTO grp_action (grp, action, doc_type)
            SELECT {:d}, {:d}, {:d}
            WHERE NOT EXISTS (
                SELECT 1
                  FROM grp_action
                 WHERE grp = {:d}
                   AND action = {:d}
                   AND doc_type = {:d});""".format(*args))
conn.commit()
