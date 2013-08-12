#----------------------------------------------------------------------
#
# $Id$
#
# One-off script to populate the new ctrp_id column of the ctgov_import
# table.
#
# BZIssue::5294 (OCECDR-3595)
#
#----------------------------------------------------------------------
import cdrdb, lxml.etree as etree, re, datetime, sys

LOGFILE = "d:/cdr/log/Request5294.log"
PATTERN = re.compile(r"^NCI-20\d\d-\d{5}$")

def logWrite(what):
    fp = open(LOGFILE, "a")
    fp.write("%s %s\n" % (datetime.datetime.now(), what))
    fp.close()

def getId(xml):
    top = etree.XML(xml.encode("utf-8"))
    for name in ("org_study_id", "secondary_id"):
        for node in top.findall("id_info/%s" % name):
            if node.text is not None:
                match = PATTERN.search(node.text.strip())
                if match:
                    return match.group(0)
    return None

conn = cdrdb.connect()
cursor = conn.cursor()
cursor.execute("""\
    SELECT nlm_id
      FROM ctgov_import
     WHERE xml IS NOT NULL
       AND ctrp_id IS NULL""")
nlmIds = [row[0] for row in cursor.fetchall()]
counter = 0
for nlmId in nlmIds:
    ctrpId = None
    cursor.execute("SELECT xml FROM ctgov_import WHERE nlm_id = ?", nlmId)
    try:
        ctrpId = getId(cursor.fetchall()[0][0])
    except Exception, e:
        logWrite("%s: %s" % (nlmId, e))
    if ctrpId:
        try:
            cursor.execute("""\
UPDATE ctgov_import
   SET ctrp_id = ?
 WHERE nlm_id = ?""", (ctrpId, nlmId))
            logWrite("found CTRP ID %s in %s" % (repr(ctrpId), nlmId))
        except Exception, e:
            logWrite("unable to store %s for %s: %s" %
                     (repr(ctrpId), nlmId, e))
    counter += 1
    sys.stderr.write("\rprocessed %d of %d clinical_trial documents" %
                     (counter, len(nlmIds)))
    if counter % 100 == 0:
        conn.commit()
conn.commit()
sys.stderr.write("\n")
