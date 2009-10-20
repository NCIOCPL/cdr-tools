#----------------------------------------------------------------------
#
# $Id$
#
# Add NCT IDs to protocol documents for the 'duplicate' rows in the
# ctgov_import table.
#
# BZIssue::1601
#
#----------------------------------------------------------------------
import cdr, cdrdb, sys, ModifyDocs

#----------------------------------------------------------------------
# The Filter class is given to the ModifyDocs.Job object, which invokes
# the getDocIds() method to retrieve a list of CDR document IDs for
# processing.
#----------------------------------------------------------------------
class Filter:
    def __init__(self, docs):
        self.docs = docs
    def getDocIds(self):
        return docs.keys()

#----------------------------------------------------------------------
# The Transform class is given to the ModifyDocs.Job object, which in
# turn gives it to each ModifyDocs.Doc object.  The run() method of
# this class takes a cdr.Doc object and returns a (possibly) modified
# copy of that object's xml member.
#
# See comment at top for this job's logic.
#----------------------------------------------------------------------
class Transform:
    def __init__(self, docs):
        self.docs = docs
    def run(self, docObj):
        cdrId = cdr.exNormalize(docObj.id)
        try:
            nctId = docs[cdrId[1]]
        except:
            sys.stderr.write("can't find NCT ID for %s\n" % docObj.id)
            return docObj.xml
        filter = """\
<?xml version='1.0' encoding='UTF-8'?>

<xsl:transform                version = '1.0' 
                            xmlns:xsl = 'http://www.w3.org/1999/XSL/Transform'
                            xmlns:cdr = 'cips.nci.nih.gov/cdr'>

 <xsl:output                   method = 'xml'/>

 <!--
 =======================================================================
 Copy most things straight through.
 ======================================================================= -->
 <xsl:template                  match = '@*|node()|comment()|
                                         processing-instruction()'>
  <xsl:copy>
   <xsl:apply-templates        select = '@*|node()|comment()|
                                         processing-instruction()'/>
  </xsl:copy>
 </xsl:template>

 <!-- Add NCT ID if not already present. -->
 <xsl:template                  match = 'ProtocolIDs'>
  <xsl:copy>
   <xsl:apply-templates        select = '@*|node()|comment()|
                                         processing-instruction()'/>
   <xsl:if                       test = 'not(OtherID
                                         [IDType = "ClinicalTrials.gov ID"])'>
    <OtherID>
     <IDType>ClinicalTrials.gov ID</IDType>
     <IDString>%s</IDString>
    </OtherID>
   </xsl:if>
  </xsl:copy>
 </xsl:template>
</xsl:transform>
""" % nctId
        if type(filter) == type(u""):
            filter = filter.encode('utf-8')
        result = cdr.filterDoc('guest', filter, doc = docObj.xml, inline = 1)
        if type(result) in (type(""), type(u"")):
            sys.stderr.write("%s: %s\n" % (docObj.id, result))
            return docObj.xml
        return result[0]

#----------------------------------------------------------------------
# Collect the documents we're interested in.
#----------------------------------------------------------------------
def collectDocs():

    conn    = cdrdb.connect()
    cursor  = conn.cursor()
    docs    = {}
    cursor.execute("""\
SELECT DISTINCT c.nlm_id, c.cdr_id
           FROM ctgov_import c
           JOIN ctgov_disposition d
             ON d.id = c.disposition
LEFT OUTER JOIN query_term t
             ON t.doc_id = c.cdr_id
            AND t.path   = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
            AND t.value  = 'ClinicalTrials.gov ID'
          WHERE d.name   = 'duplicate'
            AND c.cdr_id IS NOT NULL
            AND t.doc_id IS NULL""")
    for nlmId, cdrId in cursor.fetchall():
        docs[cdrId] = nlmId.strip()
    return docs
            
if len(sys.argv) < 3:
    sys.stderr.write("usage: %s uid pwd [LIVE]\n" % sys.argv[0])
    sys.exit(1)
docs = collectDocs()
testMode = len(sys.argv) < 4 or sys.argv[3] != "LIVE"
job = ModifyDocs.Job(sys.argv[1], sys.argv[2], Filter(docs), Transform(docs),
                     "Add NCT ID (request #1601).", testMode = testMode)
job.run()
