#----------------------------------------------------------------------
#
# $Id: Request2655.py,v 1.2 2009-09-27 19:15:36 bkline Exp $
#
# For the pilot phase of this project, provide Oncore with an Excel file that
# maps CTEP Institutions codes to CDR Organization IDs and Names. The External
# Map table with the Usage_map of CTEP_Institution_Code and the mapped CDR ID
# can be the source of this report.
#
# Also, provide Oncore with an Excel file that finds Active Person documents
# linked to the following Organizations and also the corresponding
# CTSU_Person_ID if any in the External Map table.
#
# Vanderbilt-Ingram Cancer Center - 31118
# Vanderbilt Ingram Cancer Center at Franklin 305822
#
# Barbara Ann Karmanos Cancer Institute - 31995
#
# We may add additional institutions to this report
#
# [Amended by Lakshmi 2006-11-27:]
# I noticed on the report that an Inactive Person was included - we need
# to only include Active persons. [clarifying what is meant above by the
# phrase "Active Person documents"]
#
# I should also have specified that the Person Location should not have the
# attribute of PreviousLocation = yes. Eg -
#
# CDR2050 ***REMOVED***;New York;New York
#
# Could we provide the Person's name (rather than the doc title) and the
# primary CIPS contact organization name.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2006/11/28 15:00:37  bkline
# Program to generate Excel workbook for Percipenz.
#
#----------------------------------------------------------------------
import cdrdb, ExcelWriter, sys, time, cdr, xml.dom.minidom, cdrdocobject

class Person:
    path = '/Organization/OrganizationNameInformation/OfficialName/Name'
    targetOrgs = (31118, 305822, 31995)
    def __init__(self, pdqId, ctepCode, conn):
        self.pdqId = pdqId
        self.ctepCode = ctepCode
        self.name = None
        self.org = None
        self.orgs = []
        self.active = False
        self.inScope = False
        doc = cdr.getDoc('guest', pdqId, getObject = True)
        if type(doc) in (str, unicode):
            raise Exception(doc)
        dom = xml.dom.minidom.parseString(doc.xml)
        for node in dom.documentElement.childNodes:
            if node.nodeName == 'PersonNameInformation':
                name = cdrdocobject.PersonalName(node)
                self.name = name.format()
            elif node.nodeName == 'PersonLocations':
                self.__getOrgs(node, conn)
            elif node.nodeName == 'Status':
                for child in node.childNodes:
                    if child.nodeName == 'CurrentStatus':
                        if cdr.getTextContent(child) == 'Active':
                            self.active = True
    @classmethod
    def __getOrgName(cls, orgId, conn):
        rows = cdr.getQueryTermValueForId(cls.path, orgId, conn)
        if rows:
            return rows[0].strip()
        return None

    def __getOrgs(self, node, conn):
        fragId = None
        for child in node.childNodes:
            if child.nodeName == 'CIPSContact':
                fragId = cdr.getTextContent(child).strip()
        for child in node.childNodes:
            if child.nodeName == 'OtherPracticeLocation':
                if child.getAttribute('PreviousLocation') == 'Yes':
                    continue
                locId = child.getAttribute('cdr:id')
                for grandchild in child.childNodes:
                    if grandchild.nodeName == 'OrganizationLocation':
                        orgIdAttr = grandchild.getAttribute('cdr:ref').strip()
                        if orgIdAttr:
                            orgId = cdr.exNormalize(orgIdAttr)[1]
                            self.orgs.append(orgId)
                            if orgId in Person.targetOrgs:
                                self.inScope = True
                            if fragId and locId == fragId:
                                self.org = Person.__getOrgName(orgId, conn)

conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
cursor.execute("""\
    SELECT m.value, m.doc_id, n.value
      FROM external_map m
      JOIN external_map_usage u
        ON u.id = m.usage
      JOIN query_term n
        ON n.doc_id = m.doc_id
     WHERE n.path = '/Organization/OrganizationNameInformation'
                  + '/OfficialName/Name'
       AND u.name = 'CTEP_Institution_Code'
  ORDER BY m.value""")
book = ExcelWriter.Workbook()
sheet = book.addWorksheet('CTEP Institution Codes', frozenRows = 1)
sheet.addCol(1, 100)
sheet.addCol(2, 100)
sheet.addCol(3, 450)
bold = ExcelWriter.Font(bold = True)
centered = ExcelWriter.Alignment("Center")
headingStyle = book.addStyle(font = bold, alignment = centered)
row = sheet.addRow(1)
row.addCell(1, "CTEP CODE", "String", headingStyle)
row.addCell(2, "PDQ ID", "String", headingStyle)
row.addCell(3, "Organization Name", "String", headingStyle)
rowNumber = 2
for ctepCode, pdqId, orgName in cursor.fetchall():
    row = sheet.addRow(rowNumber)
    row.addCell(1, ctepCode)
    row.addCell(2, u"CDR%d" % pdqId)
    row.addCell(3, orgName)
    rowNumber += 1
targetOrgs = ", ".join([str(o) for o in Person.targetOrgs])
cursor.execute("""\
SELECT DISTINCT o.doc_id, m.value
           FROM query_term o
LEFT OUTER JOIN external_map m
             ON m.doc_id = o.doc_id
            AND m.usage = (SELECT id
                             FROM external_map_usage
                            WHERE name = 'CTSU_Person_ID')
          WHERE o.path = '/Person/PersonLocations/OtherPracticeLocation'
                       + '/OrganizationLocation/@cdr:ref'
            AND o.int_val IN (%s)
       ORDER BY m.value, o.doc_id""" % targetOrgs)
sheet = book.addWorksheet('Venderbilt and Karmanos Persons', frozenRows = 1)
sheet.addCol(1, 100)
sheet.addCol(2, 100)
sheet.addCol(3, 450)
sheet.addCol(4, 450)
row = sheet.addRow(1)
row.addCell(1, "CTEP CODE", "String", headingStyle)
row.addCell(2, "PDQ ID", "String", headingStyle)
row.addCell(3, "Person Name", "String", headingStyle)
row.addCell(4, "Contact Organization", "String", headingStyle)
rowNumber = 2
for pdqId, ctepCode in cursor.fetchall():
    person = Person(pdqId, ctepCode, conn)
    if person.active and person.inScope:
        row = sheet.addRow(rowNumber)
        row.addCell(1, person.ctepCode or u"None")
        row.addCell(2, u"CDR%d" % person.pdqId)
        row.addCell(3, person.name)
        row.addCell(4, person.org)
        rowNumber += 1
fp = file('percipenz.xls', 'wb')
book.write(fp, True)
