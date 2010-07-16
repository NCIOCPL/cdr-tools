#----------------------------------------------------------------------
#
# $Id$
#
# "Pancreatic Cancer Trials CDRID
#
# I am attaching a list of CDRIDs (some Inscope and some CTGOV) for which we
# need a report that has some fields from the standard OSPA Spreadsheet that
# we generate
#
# CDRID Title Primary ID Additional IDs Type of Trial Phase PI Name Expected
#                                                                   Enrollment
#
# PI name in Inscope Protocols will be from LeadOrgPersonnel/Person where the
# sibling PersonRole has one of the values - Protocol Chair, Protocol Co-chair,
# Principal Investigator
#
# PI name for CTGOV Protocols will be from OverallOfficial.
# 
# Let me know if you have questions. Would appreciate getting the report by
# Monday.
#
# BZIssue::4878
#
#----------------------------------------------------------------------
import cdrdb, sys, csv, lxml.etree as etree

def fix(me):
    if not me:
        return ''
    return me.strip().encode('utf-8')

def fixList(l):
    return "; ".join([fix(m) for m in l])

class Trial:
    def __init__(self, cdrId, cursor):
        self.cdrId = cdrId
        self.title = None
        self.primaryId = None
        self.otherIds = []
        self.trialTypes = []
        self.phases = []
        self.piNames = []
        self.expectedEnrollment = None
        cursor.execute("SELECT xml FROM document WHERE id = ?", cdrId)
        docXml = cursor.fetchall()[0][0]
        tree = etree.XML(docXml.encode('utf-8'))
        self.docType = tree.tag
        if self.docType == 'InScopeProtocol':
            for node in tree.findall('ProtocolTitle[@Type="Professional"]'):
                self.title = node.text
            for node in tree.findall('ProtocolIDs'):
                for child in node.findall('PrimaryID/IDString'):
                    self.primaryId = child.text
                for child in node.findall('OtherID/IDString'):
                    self.otherIds.append(child.text)
            for node in tree.findall('ProtocolDetail/StudyCategoryName'):
                self.trialTypes.append(node.text)
            for node in tree.findall('ProtocolPhase'):
                self.phases.append(node.text)
            for node in tree.findall('ProtocolAdminInfo/ProtocolLeadOrg'):
                for child in node.findall('LeadOrgPersonnel'):
                    for role in child.findall('PersonRole'):
                        if role.text.upper() in ('PROTOCOL CHAIR',
                                                 'PROTOCOL CO-CHAIR',
                                                 'PRINCIPAL INVESTIGATOR'):
                            for person in child.findall('Person'):
                                self.piNames.append(person.text.split('[')[0])
            for node in tree.findall('ExpectedEnrollment'):
                self.expectedEnrollment = node.text
        else:
            for node in tree.findall('OfficialTitle'):
                self.title = node.text
            for node in tree.findall('IDInfo'):
                for child in node.findall('OrgStudyID'):
                    self.primaryId = child.text
                for child in node.findall('NCTID'):
                    self.otherIds.append(child.text)
                for child in node.findall('SecondaryID'):
                    self.otherIds.append(child.text)
            for node in tree.findall('PDQIndexing/StudyCategory'
                                     '/StudyCategoryName'):
                self.trialTypes.append(node.text)
            for node in tree.findall('Phase'):
                self.phases.append(node.text)
            for node in tree.findall('Sponsors/OverallOfficial/Surname'):
                self.piNames.append(node.text)
            for node in tree.findall('CTGovIndexing/CTExpectedEnrollment'):
                self.expectedEnrollment = node.text
cursor = cdrdb.connect('CdrGuest').cursor()
fp = open('Request4878.txt', 'w')
writer = csv.writer(fp)
writer.writerow(('CDRID', 'Title', 'Primary ID', 'Additional IDs',
                 'Type of Trial', 'Phase', 'PI Name', 'Expected Enrollment'))

for cdrId in (564231, 579635, 582085, 583574, 586896, 658956, 538204, 566023):
    trial = Trial(cdrId, cursor)
    writer.writerow((trial.cdrId, fix(trial.title), fix(trial.primaryId),
                     fixList(trial.otherIds), fixList(trial.trialTypes),
                     fixList(trial.phases), fixList(trial.piNames),
                     fix(trial.expectedEnrollment)))
fp.close()
