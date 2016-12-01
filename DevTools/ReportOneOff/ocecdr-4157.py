#----------------------------------------------------------------------
# Report for invalid PMID cleanup.
# JIRA::OCECDR-4157
#----------------------------------------------------------------------
import cdrdb2 as cdrdb
import requests
import time
import lxml.etree as etree
import re

class Linker:
    cursor = cdrdb.connect("CdrGuest").cursor()
    def __init__(self, pmid, citation_id, linker_id, linker_type):
        self.pmid = pmid
        self.citation_id = citation_id
        self.linker_id = linker_id
        self.linker_type = linker_type
        self.key = (self.pmid, self.citation_id, self.linker_type,
                    self.linker_id)
    def __cmp__(self, other):
        return cmp(self.key, other.key)
    @classmethod
    def fetch(cls, pmid):
        query = cdrdb.Query("query_term q", "q.doc_id", "q.int_val", "t.name")
        query.join("active_doc a", "a.id = q.doc_id")
        query.join("doc_type t", "t.id = a.doc_type")
        query.join("query_term p", "p.doc_id = q.int_val")
        query.where("p.path = '/Citation/PubmedArticle/MedlineCitation/PMID'")
        query.where("q.path like '%cdr:%ref'")
        query.where(query.Condition("p.value", pmid))
        rows = query.unique().execute(cls.cursor).fetchall()
        return [Linker(pmid, *list(row)) for row in rows]

def fetch_citation_ids():
    query = cdrdb.Query("query_term p", "p.value").unique()
    query.join("query_term q", "q.int_val = p.doc_id")
    query.join("active_doc a", "a.id = q.doc_id")
    #query.join("doc_type t", "t.id = a.doc_type")
    query.where("p.path = '/Citation/PubmedArticle/MedlineCitation/PMID'")
    query.where("q.path like '%cdr:%ref'")
    return [row[0] for row in query.execute(Linker.cursor).fetchall()]

def slice_still_at_nlm(pmids):
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    parms = {
        "db": "pubmed",
        "retmax": str(len(pmids)),
        "term": "%s[UID]" % ",".join(pmids)
    }
    r = requests.post(url, parms)
    match = re.search("<ERROR>(.*?)</ERROR>", r.content, re.DOTALL)
    if match:
        raise Exception("PMID ERROR: %s" % match.group(1))
    if not re.search("<IdList", r.content):
        raise Exception("PMID FAILURE: %s" % r.content)
    root = etree.XML(r.content)
    return set([node.text for node in root.findall("IdList/Id")])

def still_at_nlm(pmids):
    offset = 0
    batch_size = 10000
    #batch_size = 100
    verified = set()
    while offset < len(pmids):
        slice = pmids[offset:batch_size+offset]
        at_nlm = slice_still_at_nlm(slice)
        verified |= at_nlm
        offset += batch_size
        time.sleep(2)
    return verified

def main():
    pmids = fetch_citation_ids()
    confirmed = still_at_nlm(pmids)
    lost = set(pmids) - confirmed
    print len(pmids), "PMIDs found"
    print len(confirmed), "PMIDs confirmed by NLM"
    print len(lost), "PMIDs lost by NLM"
    print "PMID\tCIT ID\tLINKER\tTYPE"
    for pmid in sorted(lost):
        for linker in sorted(Linker.fetch(pmid)):
            print "%s\t%s\t%s\t%s" % (linker.pmid, linker.citation_id,
                                      linker.linker_id, linker.linker_type)

if __name__ == "__main__":
    main()
