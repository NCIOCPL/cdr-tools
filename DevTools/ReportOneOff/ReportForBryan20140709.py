#----------------------------------------------------------------------
# $Id$
# Bryan asked for the CDR documents representing active
# non-interventional clinical trials. Part of the Clinical
# Trials Search project.
#----------------------------------------------------------------------
import cdrdb

cursor = cdrdb.connect("CdrGuest").cursor()
cursor.execute("""\
SELECT DISTINCT doc_id
           FROM query_term_pub
          WHERE path = '/CTGovProtocol/CTStudyType'
            AND value <> 'Interventional'
            AND value IS NOT NULL
            AND value <> ''""")
non_interventional = set([row[0] for row in cursor.fetchall()])
cursor.execute("""\
SELECT DISTINCT doc_id
           FROM query_term_pub
           JOIN pub_proc_cg
             ON id = doc_id
          WHERE path = '/CTGovProtocol/OverallStatus'
            AND value IN ('Temporarily closed', 'Enrolling by invitation',
                          'Approved-not yet active', 'Active')""")
cdr_ids = [row[0] for row in cursor.fetchall()]
for cdr_id in cdr_ids:
    if cdr_id in non_interventional:
        cursor.execute("SELECT xml FROM document WHERE id = ?", cdr_id)
        name = "ReportForBryan20140709/%d.xml" % cdr_id
        fp = open(name, "wb")
        fp.write(cursor.fetchall()[0][0].encode("utf-8"))
        fp.close()
