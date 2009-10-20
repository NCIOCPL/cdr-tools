#----------------------------------------------------------------------
#
# $Id$
#
# Report of published clinical trial results by CTEP ID.
#
# "In our proposal to CTEP we said we would do the following:
#
#    We will also perform a one-time collection of all trials for which
#    we have a CTEP ID and for which we have a record of one or more
#    published results in the form of Pubmed citations.  We will construct
#    an XML manifest file for this collection, in the following format:
#
#      <TrialsWithResults>
#       <Trial ctepid='xxxx'>
#        <Article pmid='12345678' date='2003-09-14'/>
#        <Article pmid='23456789' date='2004-11-02'/>
#       </Trial>
#       <Trial ctepid='yyyy'>
#        <Article pmid='80808080' date='2004-08-22'/>
#       </Trial>
#       ....
#      </TrialsWithResults>
#
#    The ctepid attribute for the Trial element will contain the CTEP
#    ID for the trial.  The pmid attribute for each Article element
#    will carry the Pubmed ID for the citation of a published article
#    reporting results of the trials.  The date attribute for the
#    Article element is used to record the last time changes to the
#    Pubmed article were retrieved from NLM.
#
#    In addition, for each Trial element in this manifest document,
#    we will produce one XML file using the structure specified in
#    NLM's PUBMED DTD.  The top-level element will be PubmedArticleSet,
#    with one or more PubmedArticle child elements.
#
#    We will package all of these XML documents (including the manifest
#    document) in a compressed archive, using whichever format preferred
#    by CTEP (zip, bzipped tar, etc.) and email the package to CTEP as
#    an attachment."
#
# BZIssue::1443
#
#----------------------------------------------------------------------
import cdr, cdrdb, re, time, os, xml.dom.minidom, sys

LOGFILE = cdr.DEFAULT_LOGDIR + '/ctep.log'

dupCiteLog = file('DuplicateCitations.txt', 'w')

class Citation:
    def __init__(self, id):
        self.cdrId      = id
        self.pmid       = None
        self.articleXml = None
        self.date       = None
        lastVersions    = cdr.lastVersions('guest', 'CDR%d' % id)
        lastPub         = lastVersions[1]
        if lastPub == -1:
            raise Exception('no publishable versions for citation CDR%d' % id)
        #cdr.logwrite("Citation(%d)" % id, LOGFILE)
        doc = cdr.getDoc('guest', id, version = lastPub, getObject = True)
        errors = cdr.getErrors(doc, errorsExpected = False)
        if errors:
            raise Exception(errors)
        cursor.execute("""\
            SELECT dt
              FROM doc_version
             WHERE id = ?
               AND num = ?""", (id, lastPub))
        rows = cursor.fetchall()
        self.date = str(rows[0][0])[:10]
        dom = xml.dom.minidom.parseString(doc.xml)
        for node in dom.documentElement.childNodes:
            if node.nodeName == 'PubmedArticle':
                sink = cdr.StringSink()
                node.writexml(sink)
                self.articleXml = sink.s.encode('utf-8')
                self.pmid = Citation.extractPmid(node)
        if not self.pmid:
            raise Exception("CDR%d: no PMID found" % id)

    def extractPmid(node):
        for child in node.childNodes:
            for grandchild in child.childNodes:
                if grandchild.nodeName == 'PMID':
                    return cdr.getTextContent(grandchild)
    extractPmid = staticmethod(extractPmid)

def findCitations(id):
    lastVersions = cdr.lastVersions('guest', "CDR%010d" % id)
    lastPub = lastVersions[1]
    if lastPub == -1:
        cdr.logwrite('no publishable version for trial CDR%d' % id, LOGFILE)
        return None
    doc = cdr.getDoc('guest', id, version = lastPub, getObject = True)
    errors = cdr.getErrors(doc, errorsExpected = False, asSequence = True)
    if errors:
        for error in errors:
            cdr.logwrite('CDR%d: %s' % (id, error), LOGFILE)
        return None
    try:
        dom = xml.dom.minidom.parseString(doc.xml)
    except Exception, e:
        cdr.logwrite('CDR%d: %s' % (id, str(e)), LOGFILE)
        return None
    results = []
    pmids = {}
    for node in dom.documentElement.childNodes:
        if node.nodeName == 'PublishedResults':
            #cdr.logwrite('found PublishedResults element', LOGFILE)
            for child in node.childNodes:
                if child.nodeName == 'Citation':
                    #cdr.logwrite('found Citation element', LOGFILE)
                    citationId = child.getAttribute('cdr:ref')
                    if citationId:
                        idTuple = cdr.exNormalize(citationId)
                        if idTuple[1] not in citations:
                            try:
                                #cdr.logwrite("getting citation %s" %
                                #             citationId, LOGFILE)
                                citation = Citation(idTuple[1])
                                citations[idTuple[1]] = citation
                            except Exception, e:
                                cdr.logwrite(str(e), LOGFILE)
                                continue
                            articleXml[citation.pmid] = citation.articleXml
                        else:
                            citation = citations[idTuple[1]]
                        if citation.pmid in pmids:
                            id1 = pmids[citation.pmid].cdrId
                            id2 = citation.cdrId
                            pmid = citation.pmid
                            dupCiteLog.write("In CDR%d: citations CDR%d and "
                                             "CDR%d have %s\n" % (id, id1, id2,
                                                                  pmid))
                        else:
                            results.append((citation.pmid, citation.date))
                            pmids[citation.pmid] = citation
    return results
    
base = "TrialsWithResults-%s" % time.strftime("%Y%m%d%H%M%S")
os.mkdir(base)
pattern = re.compile(r"[-\s]")
conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
cursor.execute("""\
   SELECT DISTINCT c.doc_id, c.value
              FROM query_term c
              JOIN query_term ct
                ON ct.doc_id = c.doc_id
             WHERE c.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDString'
               AND ct.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
               AND LEFT(c.node_loc, 8) = LEFT(ct.node_loc, 8)
               AND ct.value = 'CTEP ID'""")
trials = {}
articleXml = {}
citations = {}
rows = cursor.fetchall()
counter = 0
for cdrId, ctepId in rows:
    ctepId = pattern.sub("", ctepId)
    #cdr.logwrite("looking for citations in CDR%d (CTEP ID %s)" % (cdrId,
    #                                                              ctepId),
    #             LOGFILE)
    citationList = findCitations(cdrId)
    if citationList:
        trials[ctepId] = citationList
    counter += 1
    sys.stderr.write('\rProcessed %d of %d trials' % (counter, len(rows)))
keys = trials.keys()
keys.sort()
cdr.logwrite("loaded %d citations" % len(keys))
lines = ["<TrialsWithResults>"]
for key in keys:
    articles = trials[key]
    articles.sort()
    lines.append(" <Trial ctepid='%s'>" % key.strip())
    fname = os.path.join(base, key + '.xml')
    fp = file(fname, "w")
    fp.write("<PubmedArticleSet>\n")
    for article in articles:
        lines.append("  <Article pmid='%s' date='%s'/>" % article)
        fp.write(articleXml[article[0]])
    lines.append(" </Trial>")
    fp.write("</PubmedArticleSet>\n")
    fp.close()
lines.append("</TrialsWithResults>")
file(os.path.join(base, "manifest.xml"), "w").write('\n'.join(lines) + '\n')
