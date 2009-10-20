#----------------------------------------------------------------------
#
# $Id$
#
# Report on unique organizations involved in clinical trials
#
# "We received an external request asking if we could provide the number of
# organizations that are involved in ongoing cancer clinical trials. 
#
# 1. For InscopeProtocols, we need to count the total number of unique
# organizations that are listed as LeadOrg or Participating/External Site.
#
# 2. For CTGOV Protocols, we need to count the total number of unique Lead
# Sponsor, Collaborator, and Facility elements with cdr:ref attribute. It will
# give us a good approximation.
#
# In addition, they want number of organizations involved in breast cancer and
# colorectal cancer trials.
#
# We need this next week."
#
# BZIssue::3808
#
#----------------------------------------------------------------------
import cdrdb

conn = cdrdb.connect()
cursor = conn.cursor()
conn.setAutoCommit(True)
cursor.execute("CREATE TABLE #breast (id INTEGER)")
cursor.execute("CREATE TABLE #colorectal (id INTEGER)")
cursor.execute("""\
INSERT INTO #breast 
     SELECT doc_id
       FROM query_term
      WHERE path = '/Term/PreferredName'
        AND value = 'breast cancer'""")
cursor.execute("""\
INSERT INTO #colorectal 
     SELECT doc_id
       FROM query_term
      WHERE path = '/Term/PreferredName'
        AND value = 'colorectal cancer'""")
while True:
    cursor.execute("""\
INSERT INTO #breast
     SELECT q.doc_id
       FROM query_term q
       JOIN #breast t
         ON t.id = q.int_val
      WHERE q.path = '/Term/TermRelationShip/ParentTerm' +
                     '/TermId/@cdr:ref'
        AND q.doc_id NOT IN (SELECT id FROM #breast)""")
    if not cursor.rowcount:
        break
while True:
    cursor.execute("""\
INSERT INTO #colorectal
     SELECT q.doc_id
       FROM query_term q
       JOIN #colorectal t
         ON t.id = q.int_val
      WHERE q.path = '/Term/TermRelationShip/ParentTerm' +
                     '/TermId/@cdr:ref'
        AND q.doc_id NOT IN (SELECT id FROM #colorectal)""")
    if not cursor.rowcount:
        break
trialOrgs = set()
breastOrgs = set()
colorectalOrgs = set()
cursor.execute("""\
SELECT DISTINCT o.int_val
  FROM query_term o
  JOIN query_term s
    ON o.doc_id = s.doc_id
 WHERE s.path = '/InScopeProtocol/ProtocolAdminInfo/CurrentProtocolStatus'
   AND s.value IN ('Active', 'Approved-not yet active')
   AND o.path IN ('/InScopeProtocol/ProtocolAdminInfo/' +
                  'ProtocolLeadOrg/LeadOrganizationID/@cdr:ref',
                  '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg' +
                  '/ProtocolSites/OrgSite/OrgSiteID/@cdr:ref')""")
for row in cursor.fetchall():
    trialOrgs.add(row[0])

cursor.execute("""\
SELECT DISTINCT o.int_val
  FROM query_term o
  JOIN query_term s
    ON o.doc_id = s.doc_id
  JOIN query_term t
    ON t.doc_id = s.doc_id
 WHERE s.path = '/InScopeProtocol/ProtocolAdminInfo/CurrentProtocolStatus'
   AND s.value IN ('Active', 'Approved-not yet active')
   AND o.path IN ('/InScopeProtocol/ProtocolAdminInfo/' +
                  'ProtocolLeadOrg/LeadOrganizationID/@cdr:ref',
                  '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg' +
                  '/ProtocolSites/OrgSite/OrgSiteID/@cdr:ref')
   AND t.path in ('/InScopeProtocol/ProtocolDetail/Condition/@cdr:ref',
                  '/InScopeProtocol/Eligibility/Diagnosis/@cdr:ref')
   AND t.int_val IN (SELECT id FROM #breast)""")
for row in cursor.fetchall():
    breastOrgs.add(row[0])

cursor.execute("""\
SELECT DISTINCT o.int_val
  FROM query_term o
  JOIN query_term s
    ON o.doc_id = s.doc_id
  JOIN query_term t
    ON t.doc_id = s.doc_id
 WHERE s.path = '/InScopeProtocol/ProtocolAdminInfo/CurrentProtocolStatus'
   AND s.value IN ('Active', 'Approved-not yet active')
   AND o.path IN ('/InScopeProtocol/ProtocolAdminInfo/' +
                  'ProtocolLeadOrg/LeadOrganizationID/@cdr:ref',
                  '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg' +
                  '/ProtocolSites/OrgSite/OrgSiteID/@cdr:ref')
   AND t.path in ('/InScopeProtocol/ProtocolDetail/Condition/@cdr:ref',
                  '/InScopeProtocol/Eligibility/Diagnosis/@cdr:ref')
   AND t.int_val IN (SELECT id FROM #colorectal)""")
for row in cursor.fetchall():
    colorectalOrgs.add(row[0])

cursor.execute("""\
SELECT DISTINCT o.int_val
  FROM query_term o
  JOIN query_term s
    ON o.doc_id = s.doc_id
 WHERE s.path = '/CTGovProtocol/OverallStatus'
   AND s.value IN ('Active', 'Approved-not yet active')
   AND o.path IN ('/CTGovProtocol/Location/Facility/Name/@cdr:ref',
                  '/CTGovProtocol/Sponsors/Collaborator/@cdr:ref',
                  '/CTGovProtocol/Sponsors/LeadSponsor/@cdr:ref')""")
for row in cursor.fetchall():
    trialOrgs.add(row[0])

cursor.execute("""\
SELECT DISTINCT o.int_val
  FROM query_term o
  JOIN query_term s
    ON o.doc_id = s.doc_id
  JOIN query_term t
    ON t.doc_id = s.doc_id
 WHERE s.path = '/CTGovProtocol/OverallStatus'
   AND s.value IN ('Active', 'Approved-not yet active')
   AND o.path IN ('/CTGovProtocol/Location/Facility/Name/@cdr:ref',
                  '/CTGovProtocol/Sponsors/Collaborator/@cdr:ref',
                  '/CTGovProtocol/Sponsors/LeadSponsor/@cdr:ref')
   AND t.path in ('/CTGovProtocol/PDQIndexing/Condition/@cdr:ref',
                  '/CTGovProtocol/PDQIndexing/Eligibility/Diagnosis/@cdr:ref')
   AND t.int_val IN (SELECT id FROM #breast)""")
for row in cursor.fetchall():
    breastOrgs.add(row[0])

cursor.execute("""\
SELECT DISTINCT o.int_val
  FROM query_term o
  JOIN query_term s
    ON o.doc_id = s.doc_id
  JOIN query_term t
    ON t.doc_id = s.doc_id
 WHERE s.path = '/CTGovProtocol/OverallStatus'
   AND s.value IN ('Active', 'Approved-not yet active')
   AND o.path IN ('/CTGovProtocol/Location/Facility/Name/@cdr:ref',
                  '/CTGovProtocol/Sponsors/Collaborator/@cdr:ref',
                  '/CTGovProtocol/Sponsors/LeadSponsor/@cdr:ref')
   AND t.path in ('/CTGovProtocol/PDQIndexing/Condition/@cdr:ref',
                  '/CTGovProtocol/PDQIndexing/Eligibility/Diagnosis/@cdr:ref')
   AND t.int_val IN (SELECT id FROM #colorectal)""")
for row in cursor.fetchall():
    colorectalOrgs.add(row[0])
print "%d orgs involved in ongoing trials" % len(trialOrgs)
print "%d orgs involved in ongoing breast cancer trials" % len(breastOrgs)
print "%d orgs involved in ongoing colorectal cancer trials" % len(colorectalOrgs)
