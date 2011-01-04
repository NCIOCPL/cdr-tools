#----------------------------------------------------------------------
#
# $Id$
#
# Report requested by Diana Bitenas: "In an effort to identify recipients
# for a letter to the OnCore community from NCI, can you assist with this
# time-sensitive request by executing an SQL query outputting distinct
# lead organization names (i.e., no repeats) for all Inscope documents
# with a Submission Method of "Oncore"?"
#
# BZIssue::4950
#
#----------------------------------------------------------------------
import sys, cdrdb, lxml.etree as etree, cdr

cursor = cdrdb.connect('CdrGuest').cursor()
cursor.execute("""\
    SELECT d.id
      FROM document d
      JOIN doc_type t
        ON t.id = d.doc_type
     WHERE t.name = 'InScopeProtocol'""")
docIds = [row[0] for row in cursor.fetchall()]
done = 0
leadOrgs = set()
for docId in docIds:
    cursor.execute("SELECT xml FROM document WHERE id = ?", docId)
    try:
        tree = etree.XML(cursor.fetchall()[0][0].encode('utf-8'))
        for node in tree.findall('ProtocolSources/ProtocolSource/'
                                 'SubmissionMethod'):
            if node.text == 'Oncore':
                for orgNode in tree.findall('ProtocolAdminInfo/ProtocolLeadOrg/'
                                            'LeadOrganizationID'):
                    orgId = orgNode.get('{cips.nci.nih.gov/cdr}ref')
                    leadOrgs.add(cdr.exNormalize(orgId)[1])
                break
    except Exception, e:
        sys.stderr.write("\nCDR%d: %e\n" % (docId, e))
    done += 1
    sys.stderr.write("\rprocessed %d of %d protocols" % (done, len(docIds)))
sys.stderr.write("\ncollected %d lead org IDs\n" % len(leadOrgs))
orgNames = {}
for leadOrg in leadOrgs:
    cursor.execute("""\
        SELECT value
          FROM query_term
         WHERE path = '/Organization/OrganizationNameInformation'
                    + '/OfficialName/Name'
           AND doc_id = ?""", leadOrg)
    rows = cursor.fetchall()
    if rows:
        orgNames[leadOrg] = rows[0][0]
    else:
        sys.stderr.write("Unable to find org name for CDR%d\n" % leadOrg)
orgIds = orgNames.keys()
orgIds.sort()
for orgId in orgIds:
    print "CDR%010d\t%s" % (orgId, orgNames[orgId].encode('utf-8'))
