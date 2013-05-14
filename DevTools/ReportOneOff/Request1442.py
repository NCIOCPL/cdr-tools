#----------------------------------------------------------------------
#
# $Id$
#
# One-time flat file for CTEP, mapping CTEP IDs to NCT IDs.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdrdb, re, sys

normalize = len(sys.argv) > 1 and sys.argv[1] == '--normalize'
pattern = re.compile(r"[-\s]")
conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
cursor.execute("""\
   SELECT DISTINCT c.doc_id, c.value
              FROM query_term c
              JOIN query_term ct
                ON ct.doc_id = c.doc_id
             WHERE c.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDString'
               AND ct.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
               AND LEFT(c.node_loc, 8) = LEFT(ct.node_loc, 8)
               AND ct.value = 'CTEP ID'""")
ctepIds = {}
for cdrId, ctepId in cursor.fetchall():
    ctepId = ctepId.strip()
    if normalize:
        ctepId = pattern.sub("", ctepId)
    ctepIds[ctepId] = cdrId
print "%d CTEP IDs loaded" % len(ctepIds)
cursor.execute("""\
   SELECT DISTINCT c.doc_id, c.value
              FROM query_term c
              JOIN query_term ct
                ON ct.doc_id = c.doc_id
             WHERE c.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDString'
               AND ct.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
               AND LEFT(c.node_loc, 8) = LEFT(ct.node_loc, 8)
               AND ct.value = 'ClinicalTrials.gov ID'""")
nctIds = {}
for  cdrId, nctId in cursor.fetchall():
    nctIds[cdrId] = nctId.strip()
print "%d NCT IDs loaded" % len(nctIds)
if normalize:
    name = "Request1442_With_Normalization.txt"
else:
    name = "Request1442_Without_Normalization.txt"
output = file(name, "w")
for line in file('pdq_protocols.txt'):
    id, title = line.strip().split("\t", 1)
    id = originalId = id.strip()
    if normalize:
        id = pattern.sub("", id)
    if id in ctepIds and ctepIds[id] in nctIds:
        output.write("%s\t%s\n" % (originalId, nctIds[ctepIds[id]]))
output.close()
