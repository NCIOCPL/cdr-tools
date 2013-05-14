#----------------------------------------------------------------------
#
# $Id$
#
# NCTIDS for CTEP Trials
#
# "We have yet another request from CTEP for NCTIDs for their trials Please
# query Inscope Protocols by CTEP ID to find a match and add the NCTID. If
# there is no match on the CTEP ID, we can try to match on the Original Title
# of the protocol."
#
# BZIssue::4595
#
#----------------------------------------------------------------------
import cdrdb, ExcelReader

cursor = cdrdb.connect('CdrGuest').cursor()
cursor.execute("""\
    SELECT n.value, c.value
      FROM query_term n
      JOIN query_term nt
        ON nt.doc_id = n.doc_id
       AND LEFT(nt.node_loc, 8) = LEFT(n.node_loc, 8)
      JOIN query_term c
        ON c.doc_id = n.doc_id
      JOIN query_term ct
        ON ct.doc_id = c.doc_id
       AND LEFT(ct.node_loc, 8) = LEFT(c.node_loc, 8)
     WHERE nt.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
       AND n.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDString'
       AND ct.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
       AND c.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDString'
       AND nt.value = 'ClinicalTrials.gov ID'
       AND ct.value = 'CTEP ID'""")
idMap = {}
for nctId, ctepId in cursor.fetchall():
    idMap[ctepId] = nctId
book = ExcelReader.Workbook('Protocols_With_No_NCT_Numbersv2.xls')
sheet = book[0]
first = True
for row in sheet:
    if first:
        first = False
    else:
        print "%s\t%s" % (row[0].val, idMap.get(row[0].val, ""))
