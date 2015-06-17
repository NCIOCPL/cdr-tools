#----------------------------------------------------------------------
# $Id$
# As part of the Egyptian Mau deployment, we send Gatekeeper "remove"
# instructions for all published trial documents that are blocked
# following the switch to importing trials from CTRP instead of NLM.
# Feed these IDs to a Hotfix-Remove job using the CDR Admin Publishing
# interface.
#----------------------------------------------------------------------
import cdrdb

cursor = cdrdb.connect("CdrGuest").cursor()
cursor.execute("""\
SELECT c.id
  FROM pub_proc_cg c
  JOIN document d
    ON d.id = c.id
  JOIN doc_type t
    ON t.id = d.doc_type
 WHERE d.active_status = 'I'
   AND t.name in ('InScopeProtocol', 'CTGovProtocol')""")
doc_ids = [str(row[0]) for row in cursor.fetchall()]
print "\n".join(doc_ids)
