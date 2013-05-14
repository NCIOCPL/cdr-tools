#----------------------------------------------------------------------
#
# $Id$
#
# One time update -- at a given point in time, we should grab the CDRIDs
# and the NCTIDs from a nightly download and use that information to add
# another ProtocolIDs/OtherID/IDType/ with value of ClinicalTrials.gov ID
# and populate a sibling ProtocolIDs/OtherID/IDString element with the NCTID.
#
# BZIssue::1374
#
#----------------------------------------------------------------------
import cdr, cdrdb, sys, ModifyDocs, zipfile, xml.dom.minidom

#----------------------------------------------------------------------
# Object representing interesting components of a CTGov trial document.
#----------------------------------------------------------------------
class Doc:
    def __init__(self, xmlFile, name, cursor):
        self.name          = name
        self.xmlFile       = xmlFile
        self.dom           = xml.dom.minidom.parseString(xmlFile)
        self.nlmId         = None
        self.cdrId         = None
        self.orgStudyId    = None
        self.disposition   = None
        for node in self.dom.getElementsByTagName("nct_id"):
            self.nlmId = cdr.getTextContent(node).strip()
        for node in self.dom.getElementsByTagName("org_study_id"):
            self.orgStudyId = cdr.getTextContent(node).strip()
        if self.nlmId:
            row = None
            cursor.execute("""\
            SELECT cdr_id, disposition
              FROM ctgov_import
             WHERE nlm_id = ?""", self.nlmId)
            row = cursor.fetchone()
            if row:
                self.cdrId, self.disposition = row

#----------------------------------------------------------------------
# The Filter class is given to the ModifyDocs.Job object, which invokes
# the getDocIds() method to retrieve a list of CDR document IDs for
# processing.
#----------------------------------------------------------------------
class Filter:
    def __init__(self, docs):
        self.docs = docs
    def getDocIds(self):
        return [cdr.exNormalize(id)[1] for id in docs.keys()]

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
        self.docs   = docs
    def run(self, docObj):
        try:
            nctId = docs[docObj.id]
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
    # return { 'CDR0000067172': 'NCT00004048' }
    conn    = cdrdb.connect()
    cursor  = conn.cursor()
    if len(sys.argv) < 2:
        sys.stderr.write("usage: Request1374.py zipfile-name uid pwd\n")
        sys.exit(1)
    zipName       = sys.argv[1]
    sys.argv[1:2] = []
    file          = zipfile.ZipFile(zipName)
    nameList      = file.namelist()
    docs          = {}
    for name in nameList:
        #if len(docs) > 5:
        #    break
        xmlFile = file.read(name)
        doc = Doc(xmlFile, name, cursor)
        sys.stderr.write("\rprocessed %d, processing %s      " % (len(docs),
                                                                  name))
        if (doc.nlmId and
            not doc.cdrId and
            doc.orgStudyId and
            doc.orgStudyId.startswith("CDR")):
            docs[doc.orgStudyId.encode('utf-8')] = doc.nlmId.encode('utf-8')
    sys.stderr.write("\n")
    return docs
            
docs = collectDocs()
job = ModifyDocs.Job(sys.argv[1], sys.argv[2], Filter(docs), Transform(docs),
                     "Add NCT ID (request #1374).", testMode = False)
job.run()
