import cdr
import cdrdb
import sys
import xlrd

class User:
    aliases = {
        "Isabel Lansberry": "lansberryic",
        "Linda Saucedo Burgess": "saucedol"
    }
    def __init__(self, cursor, fullname, *memberships):
        #print memberships
        self.fullname = fullname
        query = cdrdb.Query("open_usr", "name")
        query.where(query.Condition("fullname", fullname))
        rows = query.execute(cursor).fetchall()
        self.name = rows and rows[0][0] or None
        if self.name is None:
            self.name = User.aliases.get(fullname)
        if self.name is None:
            print fullname
        self.memberships = [(m and True or False) for m in memberships]
    def add_to_groups(self, groups):
        if self.name:
            for i, flag in enumerate(self.memberships):
                if flag:
                    groups[i].users.append(self.name)
cursor = cdrdb.connect("CdrGuest").cursor()
uid = sys.argv[2]
pwd = len(sys.argv) > 3 and sys.argv[3] or None
session = cdr.login(uid, pwd)
error = cdr.checkErr(session)
if error:
    print error
    sys.exit(0)
book = xlrd.open_workbook(sys.argv[1])
sheet = book.sheet_by_index(0)
comment="Used by the CDR Admin menu system software"
existing_groups = set(cdr.getGroups(session))
groups = [cdr.Group(name, comment=comment) for name in (
    "Board Manager Menu Users",
    "CIAT/OCCM Staff Menu Users",
    "Developer/SysAdmin Menu Users"
)]
for row_index in range(1, sheet.nrows):
    user = User(cursor, *[cell.value for cell in sheet.row(row_index)])
    user.add_to_groups(groups)
for group in groups:
    name = group.name
    if group.name not in existing_groups:
        name = None
    error = cdr.putGroup(session, name, group)
    if error:
        print group.name, error
    else:
        print group.name, "saved"
