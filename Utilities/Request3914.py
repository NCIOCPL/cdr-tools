#----------------------------------------------------------------------
#
# $Id$
#
# One-off report of published results for clinical trials (for CTEP)
#
# "We have a request from the Biometrics Branch in CTEP for a report of
# Published Results for CTEP studies. While they know they get updates from
# our citation service, they want to make sure that they have all the
# citations including our older ones to prepare a manuscript for publication.
#
#Parameters for the report
#
# Match the CTEP IDs in the attached spreadsheet (worksheet References
# needed)with our CTEP IDs (we might want to revisit our matching algorithm
# from previous matching exercises if a regular match does not work)
#
# For those matched citations, pick up the Published Result information and
# provide the data in an XML Format.
#
# Here's a proposed XML structure for the export
# <PublishedTrialResult>
#    <CTEPID>
#    <PDQPrimaryProtocolID>
#    <Publication> multiply occurring
#         <FormattedCitation> - Use the same logic as we use for QC reports and
#                               Exports for formatting citations
#         <PubmedID> if available
#
# Feel free to modify this struture as appropriate - this is more
# illustrative.
#
# I need to raise the priority for this so I can get it to CTEP by the end of
# the week."
#
# BZIssue::3914
#
#----------------------------------------------------------------------
import cdrdb, re, lxml.etree, ExcelReader
try:
    import lxml.etree as etree
    print "running with lxml.etree"
except:
    try:
        import xml.etree.cElementTree as etree
        print "running with standard xml.etree.cElementTree"
    except:
        import xml.etree.ElementTree as etree
        print "running with standard xml.etree.ElementTree"

def normalize(me):
    return re.sub(u"[^0-9A-Z]", "", unicode(me).upper().strip())

class Trial:
    def __init__(self, row):
        self.cdrId = None
        self.protId = u""
        self.ctepId = u""
        self.results = []
        self.relpubs = []
        ctepId = normalize(row[0])
        otherId = normalize(row[3])
        if ctepId in duplicates:
            print "can't map '%s' unambiguously" % ctepId
        elif ctepId in ctepIds:
            self.cdrId = ctepIds[ctepId]
        elif otherId in otherIds:
            self.cdrId = otherIds[otherId][1]
            print "non-CTEP ID %s: %s" % (otherId, otherIds[otherId])
        elif ctepId in protIds:
            self.cdrId = protIds[ctepId]
            print "%s is primary ID for CDR%d" % (ctepId, self.cdrId)
        elif ctepId == otherId:
            print "can't map '%s'" % ctepId
        else:
            print "can't map '%s' or '%s'" % (ctepId, otherId)
        if self.cdrId:
            self.ctepId = cdrId2CtepId.get(self.cdrId, u"")
            cursor.execute("""\
                SELECT xml
                  FROM pub_proc_cg
                 WHERE id = ?""", self.cdrId)
            rows = cursor.fetchall()
            if not rows:
                print "CDR%d not in pub_proc_cg table" % self.cdrId
            else:
                docXml = rows[0][0]
                tree = etree.fromstring(docXml.encode('utf-8'))
                for e in tree.findall('PublishedResults'):
                    self.results.append(unicode(etree.tostring(e, 'utf-8'),
                                                'utf-8'))
                for e in tree.findall('RelatedPublications'):
                    self.relpubs.append(unicode(etree.tostring(e, 'utf-8'),
                                                'utf-8'))
                for e in tree.findall('ProtocolIDs/PrimaryID/IDString'):
                    protId = e.text
                    if protId:
                        self.protId = protId
    def toxml(self):
        x = [u"""\
 <Trial CTEPID='%s' PDQPrimaryProtocolID='%s'""" %
             (self.ctepId.replace("'", "&apos;"),
              self.protId.replace("'", "&apos;"))]
        if self.results:
            x.append(u""">
""")
            for result in self.results + self.relpubs:
                x.append(u"""\
  %s
""" % result)
            x.append(u"""\
 </Trial>
""")
        else:
            x.append(u"""/>
""")
        return u"".join(x)
        
#----------------------------------------------------------------------
# Connect to the CDR database.
#----------------------------------------------------------------------
conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()

cursor.execute("""\
   SELECT DISTINCT i.doc_id, i.value, t.value
              FROM query_term_pub i
              JOIN query_term_pub t
                ON t.doc_id = i.doc_id
              JOIN active_doc a
                ON a.id = t.doc_id
             WHERE i.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDString'
               AND t.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
               AND LEFT(i.node_loc, 8) = LEFT(t.node_loc, 8)""",
               timeout = 300)
protIds = {}
cdrIds = {}
ctepIds = {}
otherIds = {}
cdrId2CtepId = {}
duplicates = set()
for cdrId, ctepId, idType in cursor.fetchall():
    protId = normalize(ctepId)
    if idType == 'CTEP ID':
        if protId in ctepIds:
            print "duplicate CTEP ID '%s' (CDR%d and CDR%d)" % (protId,
                                                                ctepIds[protId],
                                                                cdrId)
            duplicates.add(protId)
        ctepIds[protId] = cdrId
        cdrId2CtepId[cdrId] = ctepId
    elif protId in otherIds:
        otherIds[protId].append((idType, cdrId))
cursor.execute("""\
    SELECT doc_id, value
      FROM query_term_pub
      JOIN active_doc
        ON id = doc_id
     WHERE path = '/InScopeProtocol/ProtocolIDs/PrimaryID/IDString'""",
               timeout = 300)
for cdrId, protId in cursor.fetchall():
    protId = normalize(protId)
    if protId in protIds:
        duplicates.add(protId)
        print "duplicate ID '%s' (CDR%d and CDR%d)" % (protId, protIds[protId],
                                                       cdrId)
    else:
        protIds[protId] = cdrId
    cdrIds[cdrId] = protId
book = ExcelReader.Workbook('Request3914.xls')
sheet = book[0]
first = True
xmlDoc = [u"""\
<?xml version='1.0' encoding='utf-8'?>
<Trials>
"""]
for row in sheet:
    if first:
        first = False
        continue
    trial = Trial(row)
    if trial.cdrId:
        xmlDoc.append(trial.toxml())
xmlDoc.append(u"""\
</Trials>
""")
fp = open('Request3914.xml', 'w')
fp.write(u"".join(xmlDoc).encode('utf-8'))
fp.close()
