#----------------------------------------------------------------------
#
# $Id: Request1519.py,v 1.1 2005-02-17 16:09:44 bkline Exp $
#
# "To facilitate the CTEP Data export tasks, we need to add CTEPIDS to
# InScopeProtocols."
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdr, cdrdb, re, sys, ModifyDocs

#----------------------------------------------------------------------
# Patterns which are used to match up CTEP IDs with CDR protocol IDs.
#----------------------------------------------------------------------
primaryIds = [
    [re.compile("^A(\\d[A-Z\\d]*)$"), "COG"],
    [re.compile("^ACOSOG(\\d[A-Z\\d]*)$"), "ACOSOG"],
    [re.compile("^ACRIN(\\d[A-Z\\d]*)$"), "ACRIN"],
    [re.compile("^AMC(\\d[A-Z\\d]*)$"), "AMC"],
    [re.compile("^BTCG(\\d[A-Z\\d]*)$"), "BTCG"],
    [re.compile("^C(\\d{4,5})$"), "CLB"],
    [re.compile("^C(\\d{4,5})$"), "CALGB"],
    [re.compile("^C(\\d{6})$"), "NCIC"],
    [re.compile("^CALGB(\\d[A-Z\\d]*)$"), "CLB"],
    [re.compile("^CALGB(\\d[A-Z\\d]*)$"), "CALGB"],
    [re.compile("^CCG(\\d[A-Z\\d]*)$"), "CCG"],
    [re.compile("^CCG(\\d[A-Z\\d]*)$"), "COG"],
    [re.compile("^E(\\d[A-Z\\d]*)$"), "E"],
    [re.compile("^E(\\d[A-Z\\d]*)$"), "ECOG"],
    [re.compile("^E(\\d[A-Z\\d]*)$"), "ECOGE"],
    [re.compile("^E(\\d[A-Z\\d]*)$"), "EST"],
    [re.compile("^EORTC(\\d[A-Z\\d]*)$"), "EORTC"],
    [re.compile("^EST(\\d[A-Z\\d]*)$"), "EST"],
    [re.compile("^ESTP(.+)$"), "ESTP"],
    [re.compile("^GITSG(\\d[A-Z\\d]*)$"), "GITSG"],
    [re.compile("^GOG(\\d[A-Z\\d]*)$"), "GOG"],
    [re.compile("^LCSG(\\d[A-Z\\d]*)$"), "LCSG"],
    [re.compile("^MAOP(\\d[A-Z\\d]*)$"), "MAOP"],
    [re.compile("^N(\\d[A-Z\\d]*)$"), "NCCTG"],
    [re.compile("^N(\\d[A-Z\\d]*)$"), "NCCTGN"],
    [re.compile("^NABTC(\\d[A-Z\\d]*)$"), "NABTC"],
    [re.compile("^NABTT(\\d[A-Z\\d]*)$"), "NABTT"],
    [re.compile("^NCCTG(\\d[A-Z\\d]*)$"), "NCCTG"],
    [re.compile("^NCIC(\\d[A-Z\\d]*)$"), "CANNCICIND"],
    [re.compile("^NCOG(.+)$"), "NCOG"],
    [re.compile("^NSABP(.+)$"), "NSABP"],
    [re.compile("^P(\\d[A-Z\\d]*)$"), "POG"],
    [re.compile("^PBTC(\\d[A-Z\\d]*)$"), "PBTC"],
    [re.compile("^POA(\\d[A-Z\\d]*)$"), "POA"],
    [re.compile("^POG(\\d[A-Z\\d]*)$"), "POG"],
    [re.compile("^PROG(\\d[A-Z\\d]*)$"), "PROG"],
    [re.compile("^RTOG(\\d[A-Z\\d]*)$"), "RTOG"],
    [re.compile("^RTOGBR(\\d[A-Z\\d]*)$"), "RTOGBR"],
    [re.compile("^S(\\d[A-Z\\d]*)$"), "SWOG"],
    [re.compile("^S(\\d[A-Z\\d]*)$"), "SWOGS"],
    [re.compile("^SEG(.+)$"), "SEG"],
    [re.compile("^SWOG(\\d[A-Z\\d]*)$"), "SWOG"],
    [re.compile("^TRC(\\d[A-Z\\d]*)$"), "CTEPTRC"],
    [re.compile("^W(\\d[A-Z\\d]*)$"), "NCIW"]]
nciAlternates = [
    [re.compile("^(\\d+)$"), "NCI"],
    [re.compile("^B(\\d[A-Z\\d]*)$"), "NCI"],
    [re.compile("^B(\\d[A-Z\\d]*)$"), "NCIB"],
    [re.compile("^D(\\d[A-Z\\d]*)$"), "NCID"],
    [re.compile("^T(\\d[A-Z\\d]*)$"), "NCIT"],
    [re.compile("^W(\\d[A-Z\\d]*)$"), "NCIW"]]
alternates = [
    [re.compile("^CCG(\\d[A-Z\\d]*)$"), "CCG"],
    [re.compile("^INT(\\d[A-Z\\d]*)$"), "INT"]]

#----------------------------------------------------------------------
# Regular expression for characters we ignore when matching IDs.
#----------------------------------------------------------------------
unwantedChars = re.compile(r"[-\s]")

#----------------------------------------------------------------------
# Connect to the CDR database.
#----------------------------------------------------------------------
conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()

#----------------------------------------------------------------------
# Collect CDR IDs for documents which already have a CTEP ID.
#----------------------------------------------------------------------
alreadyHaveCtepId = {}
ctepIds = {}
problems = {}
cursor.execute("""\
   SELECT DISTINCT c.doc_id, c.value
              FROM query_term c
              JOIN query_term ct
                ON ct.doc_id = c.doc_id
             WHERE c.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDString'
               AND ct.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
               AND LEFT(c.node_loc, 8) = LEFT(ct.node_loc, 8)
               AND ct.value = 'CTEP ID'""", timeout = 300)
for cdrId, ctepId in cursor.fetchall():
    id = unwantedChars.sub("", ctepId).upper()
    if id in ctepIds:
        print "duplicate CTEP ID %s (CDR%d); CDR%d has %s" % (ctepId, cdrId,
                                                              ctepIds[id][0],
                                                              ctepIds[id][1])
    else:
        ctepIds[id] = (cdrId, ctepId)
    if cdrId in alreadyHaveCtepId:
        print "CDR%d has CTEP IDs %s and %s" % (cdrId,
                                                alreadyHaveCtepId[cdrId],
                                                ctepId)
    else:
        alreadyHaveCtepId[cdrId] = ctepId
msg = "%d CTEP IDs loaded\n" % len(ctepIds)
sys.stderr.write(msg)
sys.stdout.write(msg)

#----------------------------------------------------------------------
# Gather up the primary protocol IDs for the other CDR protocols.
#----------------------------------------------------------------------
cursor.execute("""\
   SELECT DISTINCT doc_id, value
              FROM query_term
             WHERE path = '/InScopeProtocol/ProtocolIDs/PrimaryID/IDString'""",
               timeout = 300)
cdrPrimaryIds = {}
for docId, protId in cursor.fetchall():
    if docId in alreadyHaveCtepId:
        continue
    id = unwantedChars.sub("", protId).upper()
    if id in cdrPrimaryIds:
        oldCdrId = cdrPrimaryIds[id][0]
        oldProtId = cdrPrimaryIds[id][1]
        cdrPrimaryIds[id][2] = True
        problems[oldCdrId] = True
        problems[docId] = True
        print ("duplicate Primary Protocol ID: CDR%d has %s; CDR%d has %s" %
               (oldCdrId, oldProtId, docId, protId))
    else:
        cdrPrimaryIds[id] = [docId, protId, False]
msg = "collected %d CDR primary IDs\n" % len(cdrPrimaryIds)
sys.stderr.write(msg)
sys.stdout.write(msg)

#----------------------------------------------------------------------
# Gather up the 'NCI alternate' protocol IDs.
#----------------------------------------------------------------------
cursor.execute("""\
   SELECT DISTINCT c.doc_id, c.value
              FROM query_term c
              JOIN query_term ct
                ON ct.doc_id = c.doc_id
             WHERE c.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDString'
               AND ct.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
               AND LEFT(c.node_loc, 8) = LEFT(ct.node_loc, 8)
               AND ct.value = 'NCI alternate'""", timeout = 300)
cdrNciAlternateIds = {}
for docId, protId in cursor.fetchall():
    if docId in alreadyHaveCtepId:
        continue
    id = unwantedChars.sub("", protId).upper()
    if id.startswith("NCIT") and len(id) > 5 and id[-1].isalpha():
        id = id[:-1]
    if id in cdrNciAlternateIds:
        oldCdrId = cdrNciAlternateIds[id][0]
        oldProtId = cdrNciAlternateIds[id][1]
        cdrNciAlternateIds[id][2] = True
        problems[oldCdrId] = True
        problems[docId] = True
        print ("duplicate NCI alternate Protocol ID: "
               "CDR%d has %s; CDR%d has %s" %
               (oldCdrId, oldProtId, docId, protId))
    else:
        cdrNciAlternateIds[id] = [docId, protId, False]
msg = "collected %d NCI alternate IDs\n" % len(cdrPrimaryIds)
sys.stderr.write(msg)
sys.stdout.write(msg)

#----------------------------------------------------------------------
# Gather up the other 'alternate' protocol IDs.
#----------------------------------------------------------------------
cursor.execute("""\
   SELECT DISTINCT c.doc_id, c.value
              FROM query_term c
              JOIN query_term ct
                ON ct.doc_id = c.doc_id
             WHERE c.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDString'
               AND ct.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
               AND LEFT(c.node_loc, 8) = LEFT(ct.node_loc, 8)
               AND ct.value = 'Alternate'""", timeout = 300)
cdrAlternateIds = {}
for docId, protId in cursor.fetchall():
    if docId in alreadyHaveCtepId:
        continue
    id = unwantedChars.sub("", protId).upper()
    if id in cdrAlternateIds:
        oldCdrId = cdrAlternateIds[id][0]
        oldProtId = cdrAlternateIds[id][1]
        cdrAlternateIds[id][2] = True
        problems[oldCdrId] = True
        problems[docId] = True
        print ("duplicate alternate Protocol ID: "
               "CDR%d has %s; CDR%d has %s" %
               (oldCdrId, oldProtId, docId, protId))
    else:
        cdrAlternateIds[id] = [docId, protId, False]
msg = "collected %d alternate IDs\n" % len(cdrAlternateIds)
sys.stderr.write(msg)
sys.stdout.write(msg)

#----------------------------------------------------------------------
# Map of CDR IDs to CTEP IDs.
#----------------------------------------------------------------------
cdrIdToCtepId = {}

#----------------------------------------------------------------------
# Walk through the CTEP list of trials and find matching CDR documents.
#----------------------------------------------------------------------
for line in open('pdq_protocols.txt'):
    ctepId, title = line.strip().split("\t", 1)
    id = unwantedChars.sub("", ctepId).upper()
    for idmap in primaryIds:
        match = idmap[0].match(id)
        if match:
            protId = "%s%s" % (idmap[1], match.group(1))
            info   = cdrPrimaryIds.get(protId)
            if info and info[2] == False:
                cdrId = info[0]
                if cdrId in cdrIdToCtepId:
                    problems[cdrId] = True
                    mappedCtepId = cdrIdToCtepId[cdrId]
                    print "CDR%d matches CTEP IDs %s and %s" % (cdrId,
                                                                mappedCtepId,
                                                                ctepId)
                else:
                    cdrIdToCtepId[cdrId] = ctepId
    for idmap in nciAlternates:
        match = idmap[0].match(id)
        if match:
            protId = "%s%s" % (idmap[1], match.group(1))
            info  = cdrNciAlternateIds.get(protId)
            if info and info[2] == False:
                cdrId = info[0]
                if cdrId in cdrIdToCtepId:
                    problems[cdrId] = True
                    mappedCtepId = cdrIdToCtepId[cdrId]
                    print "CDR%d matches CTEP IDs %s and %s" % (cdrId,
                                                                mappedCtepId,
                                                                ctepId)
                else:
                    cdrIdToCtepId[cdrId] = ctepId
    for idmap in alternates:
        match = idmap[0].match(id)
        if match:
            protId = "%s%s" % (idmap[1], match.group(1))
            info   = cdrAlternateIds.get(protId)
            if info and info[2] == False:
                cdrId = info[0]
                if cdrId in cdrIdToCtepId:
                    problems[cdrId] = True
                    mappedCtepId = cdrIdToCtepId[cdrId]
                    print "CDR%d matches CTEP IDs %s and %s" % (cdrId,
                                                                mappedCtepId,
                                                                ctepId)
                else:
                    cdrIdToCtepId[cdrId] = ctepId

#----------------------------------------------------------------------
# Don't touch any documents associated with duplicate CTEP IDs.
#----------------------------------------------------------------------
for cdrId in problems:
    if cdrId in cdrIdToCtepId:
        del cdrIdToCtepId[cdrId]

#----------------------------------------------------------------------
# Look for CTEP IDs that would end up in more than one document.
#----------------------------------------------------------------------
cdrIds = cdrIdToCtepId.keys()
for cdrId in cdrIds:
    if cdrId not in cdrIdToCtepId:
        continue
    ctepId = cdrIdToCtepId[cdrId]
    normalizedId = unwantedChars.sub("", ctepId).upper()
    if normalizedId in ctepIds:
        oldMapping = ctepIds[normalizedId]
        print "Dup. CTEP IDs: CDR%d -> %s; CDR%d -> %s" % (oldMapping[0],
                                                           oldMapping[1],
                                                           cdrId, ctepId)
        del cdrIdToCtepId[cdrId]
        if oldMapping[0] in cdrIdToCtepId:
            del cdrIdToCtepId[oldMapping[0]]
    else:
        ctepIds[normalizedId] = (cdrId, ctepId)
msg = "%d CDR documents selected for transformation\n" % len(cdrIdToCtepId)
sys.stderr.write(msg)
sys.stdout.write(msg)
cdrIds = cdrIdToCtepId.keys()
cdrIds.sort()
for cdrId in cdrIds:
    print "CDR%d\t%s" % (cdrId, cdrIdToCtepId[cdrId])
print "queued modifications sorted by CTEP ID:"
def sortByNormalizedCtepId(a, b):
    firstId = unwantedChars.sub("", cdrIdToCtepId[a]).upper()
    secondId = unwantedChars.sub("", cdrIdToCtepId[b]).upper()
    return cmp(firstId, secondId)
cdrIds = cdrIdToCtepId.keys()
cdrIds.sort(sortByNormalizedCtepId)
for cdrId in cdrIds:
    print "%-40s CDR%d" % (cdrIdToCtepId[cdrId].strip(), cdrId)
sys.exit(0)

#----------------------------------------------------------------------
# The Filter class is given to the ModifyDocs.Job object, which invokes
# the getDocIds() method to retrieve a list of CDR document IDs for
# processing.
#----------------------------------------------------------------------
class Filter:
    def __init__(self, idMap):
        self.ids = idMap.keys()
        self.ids.sort()
    def getDocIds(self):
        return self.ids

#----------------------------------------------------------------------
# The Transform class is given to the ModifyDocs.Job object, which in
# turn gives it to each ModifyDocs.Doc object.  The run() method of
# this class takes a cdr.Doc object and returns a (possibly) modified
# copy of that object's xml member.
#
# See comment at top for this job's logic.
#----------------------------------------------------------------------
class Transform:
    def __init__(self, idMap):
        self.idMap = idMap
    def run(self, docObj):
        docIds = cdr.exNormalize(docObj.id)
        filt   = """\
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

 <!-- Add CTEP ID if not already present. -->
 <xsl:template                  match = 'ProtocolIDs'>
  <xsl:copy>
   <xsl:apply-templates        select = '@*|node()|comment()|
                                         processing-instruction()'/>
   <xsl:if                       test = 'not(OtherID
                                         [IDType = "CTEP ID"])'>
    <OtherID>
     <IDType>CTEP ID</IDType>
     <IDString>%s</IDString>
    </OtherID>
   </xsl:if>
  </xsl:copy>
 </xsl:template>
</xsl:transform>
""" % self.idMap[docIds[1]]
        if type(filt) == type(u""):
            filt = filt.encode('utf-8')
        result = cdr.filterDoc('guest', filt, doc = docObj.xml, inline = 1)
        if type(result) in (type(""), type(u"")):
            raise Exception(result)
        return result[0]
#ModifyDocs.DEBUG = True
if len(sys.argv) < 4 or sys.argv[3] not in ('test', 'live'):
    sys.stderr.write("usage: Request1519.py uid pwd test|live\n")
    sys.exit(1)
testMode        = sys.argv[3] == 'test'
filterObject    = Filter(cdrIdToCtepId)
transformObject = Transform(cdrIdToCtepId)
job = ModifyDocs.Job(sys.argv[1], sys.argv[2], filterObject, transformObject,
                     "Adding CTEP ID (request #1519).",
                     testMode = testMode)
sys.stdout.flush()
job.run()
