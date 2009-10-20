#----------------------------------------------------------------------
#
# $Id$
#
# Re-import citations invalidated by most recent DTD modifications at
# NLM (see CDR request #622); only change resulting in invalid CDR
# docs is that the URL element is no longer allowed of PubmedData
# elements.  This is the first of two steps.  After this script
# fetches the replacement citations from NLM, use ReimportCitations.py
# to actually import the Citations back into the CDR.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------

import os, cdr, cdrdb, urllib

dir     = 'ReplacementCitations'
host    = 'www.ncbi.nlm.nih.gov'
app     = '/entrez/utils/pmfetch.fcgi'
base    = 'http://' + host + app + '?db=PubMed&report=sgml&mode=text&id='
log     = open("GetReplacementCitations.log", "w")
try:
    os.mkdir(dir)
except:
    pass

# original query; takes a while so we saved it first.
"""
   SELECT DISTINCT d.id, MAX(p.int_val) AS pmid
              INTO xCitationsWithUrlElements
              FROM document d
              JOIN doc_type t
                ON t.id = d.doc_type
              JOIN query_term p
                ON p.doc_id = d.id
             WHERE t.name = 'Citation'
               AND d.xml LIKE '%URL%'
               AND p.path = '/Citation/PubmedArticle/MedlineCitation/PMID'
          GROUP BY d.id
"""

conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
cursor.execute("SELECT id, pmid FROM xCitationsWithUrlElements")

rows = cursor.fetchall()
log.write("checking %d citations\n" % len(rows))
for row in rows:
    try:
        resp = cdr.valDoc('guest', 'Citation', row[0], valLinks = 'N')
        errs = cdr.getErrors(resp, 0)
        if not errs:
            log.write("document %d is already valid\n" % row[0])
            continue
    except:
        log.write("exception caught validating %d\n" % row[0])
        continue
    url = "%s%d" % (base, row[1])
    try:
        uobj = urllib.urlopen(url)
        page = uobj.read()
    except:
        log.write("failure retrieving PMID %d from Pubmed for CDR%d\n"
                  % (row[1], row[0]))
        continue
    if not page:
        log.write("failure retrieving PMID %d from Pubmed for CDR%d\n"
                  % (row[1], row[0]))
        continue
    f = open("%s/%d.xml" % (dir, row[0]), "wb")
    f.write(page)
    f.close()
    log.write("imported PMID %d for CDR%d\n" % (row[1], row[0]))
