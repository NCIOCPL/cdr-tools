#----------------------------------------------------------------------
#
# $Id: Request3946.py,v 1.1 2008-02-25 18:35:13 bkline Exp $
#
# Urgent report for CCR.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import ExcelWriter, cdrdb, cdr
etree = cdr.importEtree()

def getChildText(e, name):
    child = e.find(name)
    if child is not None:
        return child.text.strip().replace(u"\n", u" ").replace(u"\r", u"")
    return u""

class Protocol:
    class PrimaryId:
        def __init__(self, elem):
            self.value   = getChildText(elem, 'IDString')
            self.comment = getChildText(elem, 'Comment')
    class OtherId:
        def __init__(self, elem):
            self.value = getChildText(elem, 'IDString')
            self.type  = getChildText(elem, 'IDType')
        def format(self):
            return u"%s (type %s)" % (self.value, self.type)
    def __init__(self, cursor, docId, docVersion):
        self.docId = docId
        self.title = None
        self.status = None
        self.sponsors = []
        self.comment = None
        self.primaryId = None
        self.alternateIds = []
        cursor.execute("""
            SELECT xml
              FROM doc_version
             WHERE id = ?
               AND num = ?""", (docId, docVersion))
        docXml = cursor.fetchall()[0][0]
        tree = etree.fromstring(docXml.encode('utf-8'))
        protIds = tree.find('ProtocolIDs')
        if protIds:
            for child in protIds.iterchildren():
                if child.tag == 'PrimaryID':
                    self.primaryId = Protocol.PrimaryId(child)
                elif child.tag == 'OtherID':
                    self.alternateIds.append(Protocol.OtherId(child))
        for child in tree.findall('ProtocolTitle'):
            if child.attrib['Type'] == 'Original':
                self.title = child.text.strip().replace("\n", " ")
        for node in tree.findall('ProtocolAdminInfo'):
            for child in node.findall('CurrentProtocolStatus'):
                self.status = child.text.strip()
        for node in tree.findall('ProtocolSponsors'):
            for child in node.iterchildren():
                if child.tag == 'SponsorName' and child.text:
                    self.sponsors.append(child.text.strip())
                elif child.tag == 'Comment' and child.text:
                    self.comment = child.text.strip()
    def formatPrimaryId(self):
        if not self.primaryId:
            return u""
        if self.primaryId.comment:
            return "%s (%s)" % (self.primaryId.value, self.primaryId.comment)
        return self.primaryId.value
    def formatAlternateIds(self):
        return u"; ".join(i.format() for i in self.alternateIds)
    def formatSponsors(self):
        sponsors = u"; ".join(self.sponsors)
        if sponsors:
            if self.comment:
                return u"%s (%s)" % (sponsors, self.comment)
            return sponsors
        return self.comment

cursor = cdrdb.connect('CdrGuest').cursor()
cursor.execute("""\
  SELECT MAX(v.num), s1.doc_id
    FROM query_term_pub s1
    JOIN query_term_pub s2
      ON s1.doc_id = s2.doc_id
    JOIN query_term_pub s3
      ON s1.doc_id = s3.doc_id
    JOIN active_doc a
      ON s1.doc_id = a.id
    JOIN doc_version v
      ON s1.doc_id = v.id
   WHERE s1.path = '/InScopeProtocol/ProtocolSponsors/SponsorName'
     AND s2.path = '/InScopeProtocol/ProtocolSponsors/SponsorName'
     AND s3.path = '/InScopeProtocol/ProtocolSources/ProtocolSource/SourceName'
     AND s1.value = 'NCI'
     AND s2.value = 'Pharmaceutical/Industry'
     AND s3.value IN ('NCI-CCR', 'NCI-CTEP')
     AND v.publishable = 'Y'
GROUP BY s1.doc_id
ORDER BY s1.doc_id""", timeout = 300)
protocols = []
for docVersion, docId in cursor.fetchall():
    protocols.append(Protocol(cursor, docId, docVersion))
book = ExcelWriter.Workbook()
sheet = book.addWorksheet('CCR Sponsor Report')
sheet.addCol(1, 60)
sheet.addCol(2, 300)
sheet.addCol(3, 200)
sheet.addCol(4, 200)
sheet.addCol(5, 200)
sheet.addCol(6, 100)
bold = ExcelWriter.Font(bold = True)
centered = ExcelWriter.Alignment("Center")
alignment = ExcelWriter.Alignment("Left", "Top", True)
dataStyle = book.addStyle(alignment = alignment)
headingStyle = book.addStyle(font = bold, alignment = centered)
row = sheet.addRow(1)
row.addCell(1, "CDR ID", "String", headingStyle)
row.addCell(2, "Original Title", "String", headingStyle)
row.addCell(3, "Primary ID", "String", headingStyle)
row.addCell(4, "Alternate IDs", "String", headingStyle)
row.addCell(5, "Sponsors", "String", headingStyle)
row.addCell(6, "Status", "String", headingStyle)
rowNum = 2
for protocol in protocols:
    row = sheet.addRow(rowNum)
    rowNum += 1
    row.addCell(1, protocol.docId, "String", dataStyle)
    row.addCell(2, protocol.title, "String", dataStyle)
    row.addCell(3, protocol.formatPrimaryId(), "String", dataStyle)
    row.addCell(4, protocol.formatAlternateIds(), "String", dataStyle)
    row.addCell(5, protocol.formatSponsors(), "String", dataStyle)
    row.addCell(6, protocol.status, "String", dataStyle)
fp = file('d:/Inetpub/wwwroot/Request3946.xls', 'wb')
book.write(fp, True)
fp.close()
