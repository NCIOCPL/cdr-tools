#----------------------------------------------------------------------
#
# $Id$
#
# Collect lookup values for CTS system and upload them to the CTS server.
#
# BZIssue::1925
#
#----------------------------------------------------------------------
import cdrdb, sys, xml.dom.minidom, time, re, pickle, bz2, cdrmailcommon

conn      = cdrdb.connect('CdrGuest')
cursor    = conn.cursor()
tables    = []
wsPattern = re.compile("\\s+")
start     = time.time()

#----------------------------------------------------------------------
# Collect pharma sponsors.
#----------------------------------------------------------------------
cursor.execute("""\
    SELECT d.id, d.title
      FROM document d
      JOIN query_term t
        ON t.doc_id = d.id
     WHERE t.path = '/Organization/OrganizationType'
       AND t.value = 'Pharmaceutical/biomedical'
  ORDER BY d.title, d.id""")
rows = []
for row in cursor.fetchall():
    rows.append((row[0], wsPattern.sub(u' ', row[1].strip()).encode('utf-8')))
tables.append(('pharma', rows))

#----------------------------------------------------------------------
# Collect lead organization names.
#----------------------------------------------------------------------
class Org:
    cursor = cdrdb.connect('CdrGuest').cursor()
    def __init__(self, docId, docVer, docTitle):
        self.docId = docId
        self.docVer = docVer
        docTitle = wsPattern.sub(u" ", docTitle)
        name, location = docTitle.split(u';', 1)
        self.name = name.strip()
        if location.find(u';') != -1:
            city, state = location.split(u';', 1)
            self.city = city.strip()
            self.state = state.strip()
        else:
            self.city = None
            self.state = location.strip()
        if self.city:
            self.loc = u"(%s, %s)" % (self.city, self.state)
        else:
            self.loc = u"(%s)" % self.state
        Org.cursor.execute("""
            SELECT value
              FROM query_term_pub
             WHERE path = '/Organization/OrganizationNameInformation'
                        + '/AlternateName'
               AND doc_id = ?""", docId)
        upperName = self.name.upper()
        self.allNames = { self.name.upper(): self.name }
        for row in Org.cursor.fetchall():
            altName = wsPattern.sub(u" ", row[0])
            nameKey = altName.upper()
            if nameKey not in self.allNames:
                self.allNames[nameKey] = altName
            
cursor.execute("""\
             SELECT v.id, v.num, v.title
               FROM doc_version v
               JOIN doc_type t
                 ON t.id = v.doc_type
               JOIN document d
                 ON d.id = v.id
              WHERE t.name = 'Organization'
                AND v.title NOT LIKE 'Inactive;%'
                AND d.active_status = 'A'
                AND v.num = (SELECT MAX(num)
                               FROM doc_version
                              WHERE id = v.id
                                AND v.publishable = 'Y'
                                AND v.val_status = 'V')""", timeout = 500)
rows  = cursor.fetchall()
n     = 0
orgs  = []
names = []
for docId, docVer, docTitle in rows:
    org = Org(docId, docVer, docTitle)
    name = u"%s %s" % (org.name, org.loc)
    orgs.append((org.docId, name.encode('utf-8')))
    for key in org.allNames:
        name = u"%s %s" % (org.allNames[key], org.loc)
        names.append((org.docId, name.encode('utf-8')))
    n += 1
    sys.stderr.write("\rprocessed %d of %d documents" % (n, len(rows)))
tables.append(('org', orgs))
tables.append(('org_name', names))

#----------------------------------------------------------------------
# Collect person values.
#----------------------------------------------------------------------
class Person:
    def __init__(self, docId, docTitle):
        self.docId = docId
        docTitle = wsPattern.sub(u' ', docTitle.strip())
        name, location = docTitle.split(u';', 1)
        surname, forename = name.split(u', ', 1)
        self.surname = surname.strip()
        self.forename = forename.strip()
        if location.find(u';') != -1:
            city, state = location.split(u';', 1)
            self.city = city.strip()
            self.state = state.strip()
        else:
            self.city = None
            self.state = location.strip()
        if self.city:
            display = u"%s, %s (%s, %s)" % (self.surname, self.forename,
                                            self.city, self.state)
        else:
            display = u"%s, %s (%s)" % (self.surname, self.forename,
                                        self.state)
        self.display = display
        
conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
cursor.execute("""\
             SELECT v.id, v.title
               FROM doc_version v
               JOIN doc_type t
                 ON t.id = v.doc_type
               JOIN document d
                 ON d.id = v.id
              WHERE t.name = 'Person'
                AND v.title NOT LIKE 'Inactive;%'
                AND d.active_status = 'A'
                AND v.num = (SELECT MAX(num)
                               FROM doc_version
                              WHERE id = v.id
                                AND v.publishable = 'Y'
                                AND v.val_status = 'V')""", timeout = 500)
rows = cursor.fetchall()
n = 0
people = []
for docId, docTitle in rows:
    person = Person(docId, docTitle)
    people.append((person.docId, person.surname.encode('utf-8'),
                   person.forename.encode('utf-8'),
                   person.display.encode('utf-8')))
    n += 1
    sys.stderr.write("\rprocessed %d of %d documents" % (n, len(rows)))
tables.append(('person', people))

#----------------------------------------------------------------------
# Store the values on the CTS server.
#----------------------------------------------------------------------
bytes   = pickle.dumps(tables)
bytes   = bz2.compress(bytes)
fp = open('CtsLookupValues.pickle.bz2', 'wb')
fp.write(bytes)
fp.close()
conn    = cdrmailcommon.emailerConn('dropbox')
cursor  = conn.cursor()
cursor.execute("""\
    INSERT INTO cts_lookup_values (pickle, uploaded)
         VALUES (%s, NOW())""", bytes)
conn.commit()
elapsed = time.time() - start
print "\nelapsed: %f" % elapsed
