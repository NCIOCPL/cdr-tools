import cdr, cdrdb

session = cdr.login('rmk', 'apple$zebra')
comment = 'document created for CDR task 4926'
cursor = cdrdb.connect('CdrGuest').cursor()
cursor.execute("SELECT id FROM document WHERE comment = ?", comment)
rows = cursor.fetchall()
namespace = "cips.nci.nih.gov/cdr"
for row in rows:
    docId = row[0]
    doc = cdr.getDoc(session, docId, 'Y')
    doc = doc.replace("audience='Patient'", "audience='Patients'")
    doc = doc.replace('audience="Patient"', 'audience="Patients"')
    doc = doc.replace('<Media>', '<Media xmlns:cdr="%s">' % namespace)
    x = cdr.repDoc(session, doc=doc, val='Y', ver='Y', verPublishable='Y',
               checkIn='Y', showWarnings=True)
    print(x)
    #break
