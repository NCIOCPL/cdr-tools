#----------------------------------------------------------------------
#
# $Id:$
#
# Global change to strip the Compact attribute from lists.
#
# JIRA::OCECDR-3925
#
#----------------------------------------------------------------------
import cdrdb
import time

start = time.time()
cursor = cdrdb.connect("CdrGuest").cursor()
cursor.execute("""\
SELECT id
  FROM document
 WHERE xml LIKE '%list%compact%'""")
ids = [row[0] for row in cursor.fetchall()]
print len(ids), time.time() - start
