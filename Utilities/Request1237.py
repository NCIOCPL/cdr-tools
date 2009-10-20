#----------------------------------------------------------------------
#
# $Id$
#
# We need two ad hoc queries to check some details on BACH
#
# 1. List of PUPs who have Links from Protocols to multiple fragments in
#    Person records -- we will need DocID, PUP Name, UpdateMode, Protocol
#    DOcID and Target Person Fragment ID
#
# 2. List of PUPs where the Center for Cancer Research (27842) is the
#    lead org for a protocol. List DocID, Name, UpdateMode, Protocol Doc ID
#
# BZIssue::1237
#
#----------------------------------------------------------------------
import cdrdb, sys

class UpdateMode:
    def __init__(self, modeName, modeType):
        self.modeName = modeName
        self.modeType = modeType
    def __str__(self):
        return "%s: %s" % (self.modeType, self.modeName)

class ProtocolLink:
    def __init__(self, id, pupLink, nodeLoc):
        self.id      = id
        self.pupLink = pupLink
        self.modes   = self.__getModes(id, nodeLoc)
    def __getModes(self, id, nodeLoc):
        modes = []
        cursor.execute("""\
            SELECT m.value, t.value
              FROM query_term m
              JOIN query_term t
                ON m.doc_id = t.doc_id
               AND LEFT(m.node_loc, 12) = LEFT(t.node_loc, 12)
             WHERE m.doc_id = ?
               AND m.path = '/InScopeProtocol/ProtocolAdminInfo'
                          + '/ProtocolLeadOrg/UpdateMode'
               AND t.path = '/InScopeProtocol/ProtocolAdminInfo'
                          + '/ProtocolLeadOrg/UpdateMode/@MailerType'
               AND LEFT(m.node_loc, 8) = '%s'""" % nodeLoc[:8],  id)
        for row in cursor.fetchall():
            modes.append(UpdateMode(row[0], row[1]))
        return modes

class PUP:
    def __init__(self, id, name):
        self.id    = id
        self.name  = name
        self.modes = self.__getModes(id)
        self.links = self.__getLinks(id)
    def __getModes(self, id):
        modes = []
        cursor.execute("""\
            SELECT m.value, t.value
              FROM query_term m
              JOIN query_term t
                ON m.doc_id = t.doc_id
               AND LEFT(m.node_loc, 8) = LEFT(t.node_loc, 8)
             WHERE m.doc_id = ?
               AND m.path = '/Person/PersonLocations/UpdateMode'
               AND t.path = '/Person/PersonLocations/UpdateMode'
                          + '/@MailerType'""",
                       id)
        for row in cursor.fetchall():
            modes.append(UpdateMode(row[0], row[1]))
        return modes
    def __getLinks(self, id):
        links = []
        cursor.execute("""\
            SELECT u.doc_id, u.value, u.node_loc
              FROM query_term u
              JOIN query_term r
                ON r.doc_id = u.doc_id
               AND LEFT(r.node_loc, 12) = LEFT(u.node_loc, 12)
             WHERE r.path  = '/InScopeProtocol/ProtocolAdminInfo'
                           + '/ProtocolLeadOrg/LeadOrgPersonnel/PersonRole'
               AND u.path  = '/InScopeProtocol/ProtocolAdminInfo'
                           + '/ProtocolLeadOrg/LeadOrgPersonnel'
                           + '/Person/@cdr:ref'
               AND r.value = 'Update person'
               AND u.int_val = ?
          ORDER BY u.doc_id, u.value""", id)
        for row in cursor.fetchall():
            links.append(ProtocolLink(row[0], row[1], row[2]))
        return links
    def report(self):
        id = str(self.id)
        name = self.name.encode('utf-8')
        #semi = name.find(';')
        #if semi != -1:
        #    name = name[:semi]
        modes = "; ".join([str(m) for m in self.modes])
        for link in self.links:
            sys.stdout.write("%s\t%s\t%s\t%s\t%s\t%s\n" %
                             (id, name, modes, link.id, link.pupLink,
                              "; ".join([str(m) for m in link.modes])))
            id = name = modes = ""
            
conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
cursor.execute("CREATE TABLE #t (n INTEGER, id INTEGER, link VARCHAR(255))")
conn.commit()
cursor.execute("""\
    INSERT INTO #t
    SELECT COUNT(*), u.int_val, u.value
      FROM query_term u
      JOIN query_term r
        ON r.doc_id = u.doc_id
       AND LEFT(r.node_loc, 12) = LEFT(u.node_loc, 12)
     WHERE r.path  = '/InScopeProtocol/ProtocolAdminInfo'
                   + '/ProtocolLeadOrg/LeadOrgPersonnel/PersonRole'
       AND u.path  = '/InScopeProtocol/ProtocolAdminInfo'
                   + '/ProtocolLeadOrg/LeadOrgPersonnel/Person/@cdr:ref'
       AND r.value = 'Update person'
  GROUP BY u.int_val, u.value""", timeout = 600)
conn.commit()
cursor.execute("""\
    SELECT t.id, d.title, COUNT(*)
      FROM #t t
      JOIN document d
        ON t.id = d.id
--  ORDER BY t.id
  GROUP BY t.id, d.title
    HAVING COUNT(*) > 1""")
rows = cursor.fetchall()
for row in rows:
    pup = PUP(row[0], row[1])
    pup.report()
