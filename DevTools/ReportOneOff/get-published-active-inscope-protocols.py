import cdrdb

cursor = cdrdb.connect("CdrGuest").cursor()
cursor.execute("""\
SELECT doc_id
  FROM query_term_pub
  JOIN pub_proc_cg
    ON id = doc_id
 WHERE path = '/InScopeProtocol/ProtocolAdminInfo/CurrentProtocolStatus'
   AND value IN ('Enrolling by invitation',
                 'Active',
                 'Approved-not yet active')""")
for row in cursor.fetchall():
    print row[0]
