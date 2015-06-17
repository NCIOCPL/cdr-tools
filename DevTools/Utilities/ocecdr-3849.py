#----------------------------------------------------------------------
# $Id$
#
# Database updates for integration with NIH Active Directory
#
# JIRA::OCECDR-3849
#----------------------------------------------------------------------
import cdrdb
import sys
import time

inactive_accounts = set([
    "CBIITguest",
    "CIATguest",
    "TermGuest",
    "bferguson",
    "bmacy",
    "bret",
    "cbiit",
    "dphillips",
    "dprice",
    "jferguson",
    "mzeleski",
    "nciweb",
    "rchen",
    "sgottesman",
    "tempry",
    "wbao"
])

machine_accounts = set([
    "CTGovImport",
    "CdrGuest",
    "CdrService",
    "ExternalImporter",
    "GPImport",
    "VerifMailer",
    "cdrmailers",
    "etracker",
    "operator",
    "SchemaUpdater"
])

user_map = {
    "rmk": "bkline",
    "ahm": "alan",
    "lgrama": "lgrama",
    "vshields": "vshields",
    "mtapia": "tapiam",
    "jstringer": "morrisj3",
    "akuhlmann": "kuhlmanna",
    "venglisc": "volker",
    "cboggess": "boggessc",
    "mbeckwit": "mbeckwit",
    "mtrivedi": "trivedim",
    "dblais": "dblais",
    "jmarcus": "marcusj",
    "rbaldwin": "robin",
    "vdyer": "dyerv",
    "rmanrow": "rmanrow",
    "skasner": "squint",
    "sneill": "neills",
    "woseipoku": "oseipokuw",
    "lsaucedo": "saucedol",
    "amiddleswarth": "amiddles",
    "mbarnstead": "barnsteadm",
    "lmullican": "mullicanl",
    "nyu": "yun3",
    "efelker": "felkerm",
    "rharrison": "juther",
    "kbroun": "brounk",
    "vimasduch": "imasduchovnyv",
    "dmcgrath": "dmcgrath",
    "anjamison": "JamisonA",
    "stbucher": "buchers",
    "cfoushee": "fousheeC2",
    "dbeebe": "beebedp",
    "tsmith": "smitht5",
    "jacosta": "acostaj",
    "myousufzai": "yousufzaimg",
    "kgrayson": "graysonka",
    "Bonnief": "fergusonbc",
    "cnorwood": "evanscd",
    "erhoysa": "hoysaem",
    "kreyes": "reyesk",
    "mizbicki": "izbickimj",
    "rchasan": "rchasan",
    "gottesmansb": "gottesmansb",
    "jbocinski": "bocinskij",
    "learnb": "learnb",
    "ddo": "dod",
    "dvismer": "vismerd",
    "ehenry": "henryec",
    "hmcauliffe": "mcauliffehl",
    "lcheryan": "cheryanlf",
    "lburack": "buracklb",
    "vsun": "sunvw",
    "lansberryic": "lansberryic",
}
class User:
    def __init__(self, row):
        (self.id, self.name, self.fullname, self.expired,
         self.password, self.hashedpw) = row
        self.changed = False
        self.nih_name = None

direct = len(sys.argv) > 1 and sys.argv[1] == "direct"
if direct:
    conn = cdrdb.connect()
    cursor = conn.cursor()
    usr_legacy = "xusr_legacy_%s" % time.strftime("%Y%m%d%H%M%S")
    cursor.execute("SELECT * INTO %s FROM usr" % usr_legacy)
    cursor.execute("GRANT SELECT ON %s TO CdrGuest" % usr_legacy)
else:
    print """\
IF EXISTS (SELECT *
             FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = 'xusr_legacy')
DROP TABLE xusr_legacy;
GO
SELECT * INTO xusr_legacy FROM usr;
GO"""
query = cdrdb.Query("usr", "id", "name", "fullname", "expired", "password",
                    "hashedpw")
active = {}
for row in query.execute().fetchall():
    user = User(row)
    if not user.expired:
        active[user.name] = user
for name in sorted(active):
    if name in user_map:
        if direct:
            cursor.execute("""\
UPDATE usr
   SET name = ?,
       password = '',
       hashedpw = HASHBYTES('SHA1', '')
 WHERE name = ?""", (user_map[name], name))
            print "updated row for %s" % user_map[name]
        else:
            print ("UPDATE usr SET name = '%s', password = '', "
                   "hashedpw = HASHBYTES('SHA1', '') WHERE name = '%s';" %
                   (user_map[name], name))
    elif name not in machine_accounts:
        sys.stderr.write("%s (%s) not mapped\n" % (name, active[name].fullname))
if direct:
    conn.commit()
else:
    print "GO"
