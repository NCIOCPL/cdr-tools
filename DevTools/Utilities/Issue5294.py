#----------------------------------------------------------------------
#
# $Id$
#
# Script to populate new ctrp_id column in ctgov_import table.
#
# BZIssue::5294
#
#----------------------------------------------------------------------
import cdrdb, lxml.etree as etree, re, sys

pattern = re.compile("NCI-\\d+-\\d+")
conn = cdrdb.connect()
cursor = conn.cursor()
cursor.execute("SELECT nlm_id FROM ctgov_import WHERE xml IS NOT NULL")
nctIds = [row[0] for row in cursor.fetchall()]
counter = 0
for nctId in nctIds:
    cursor.execute("SELECT xml FROM ctgov_import WHERE nlm_id = ?", nctId)
    xml = cursor.fetchall()[0][0]
    tree = etree.XML(xml.encode("utf-8"))
    ctrpIds = []
    for ids in tree.findall("id_info"):
        for i in ids:
            try:
                text = i.text.strip()
                if pattern.match(text.upper()):
                    ctrpIds.append((i.tag, text))
                    if len(text) != 14:
                        sys.stderr.write("\n%s: %s\n" % (nctId, text))
                    if text != text.upper():
                        sys.stderr.write("\n%s: %s\n" % (nctId, text))
            except Exception, e:
                sys.stderr.write("\nEXCEPTION FOR %s (%s): %s\n" % (nctId,
                                                                    repr(i),
                                                                    e))
    if len(ctrpIds) > 1:
        sys.stderr.write("\n%s: %s\n" % (nctId, repr(ctrpIds)))
    if ctrpIds:
        print "%s\t%s\t%s" % (nctId, ctrpIds[0][1], ctrpIds[0][0])
        cursor.execute("""\
UPDATE ctgov_import
   SET ctrp_id = ?
 WHERE nlm_id = ?""", (ctrpIds[0][1], nctId))
    counter += 1
    sys.stderr.write("\rprocessed %d of %d documents" % (counter, len(nctIds)))
conn.commit()
