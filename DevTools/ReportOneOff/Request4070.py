#----------------------------------------------------------------------
#
# $Id$
#
# Report on trials in the CDR
#
# "We need a report that list trials with several of their elements displayed,
# in order to help assess how much time CIAT will need to add new, required
# CTGov elements into the InScopeProtocol documents.
#
# The report should be of all 'Active', 'Approved-not yet active', 'Temporarily
# closed' trials that were ongoing as of or after Sept 26th 2007.
#
# It will need to include:
#
#    CDR ID
#    Doc title
#    Protocol Design
#    Phase
#    Study type
#    Study Category Name
#    ProtocolSource/SourceName
#    Person name (who has role of "Update Person")
#    Country (from Person record of Update Person)
#    Current Protocol Status"
#
# BZIssue::4070
#
#----------------------------------------------------------------------
import cdrdb, cdrdocobject, ExcelWriter, xml.dom.minidom, sys

cursor = cdrdb.connect('CdrGuest').cursor()
docCursor = cdrdb.connect('CdrGuest').cursor()
cursor.execute("""\
    SELECT d.id
      FROM document d
      JOIN doc_type t
        ON t.id = d.doc_type
     WHERE t.name = 'InScopeProtocol'
  ORDER BY d.id DESC""")
book = ExcelWriter.Workbook()
sheet = book.addWorksheet('Request 4070')
style = book.addStyle(font = ExcelWriter.Font(bold = True))
sheet.addCol(1, 50)
sheet.addCol(2, 400)
sheet.addCol(3, 100)
sheet.addCol(4, 75)
sheet.addCol(5, 100)
sheet.addCol(6, 150)
sheet.addCol(7, 125)
sheet.addCol(8, 100)
sheet.addCol(9, 50)
sheet.addCol(10, 125)
sheet.addCol(11, 125)
sheet.addCol(12, 75)
row = sheet.addRow(1, style)
row.addCell(1, 'CDR ID', style)
row.addCell(2, 'Doc Title', style)
row.addCell(3, 'Protocol Design(s)', style)
row.addCell(4, 'Phase(s)', style)
row.addCell(5, 'Study Type(s)', style)
row.addCell(6, 'Study Category Name(s)', style)
row.addCell(7, 'Protocol Sources', style)
row.addCell(8, 'PUP Name', style)
row.addCell(9, 'Country', style)
row.addCell(10, 'Current Protocol Status', style)
row.addCell(11, 'First Published', style)
row.addCell(12, 'IND Number', style)

rowNum = 2
style = book.addStyle(alignment = ExcelWriter.Alignment('Left', 'Top', True))
row = cursor.fetchone()
pups = {}
while row:
    docId = row[0]
    docCursor.execute("""\
        SELECT title, xml, first_pub
          FROM document
         WHERE id = ?""", docId)
    title, docXml, firstPub = docCursor.fetchone()
    dom = xml.dom.minidom.parseString(docXml.encode('utf-8'))
    p = cdrdocobject.Protocol(docId, dom.documentElement)
    if p.hadStatus("2007-09-26", "2008-05-02"):
        docCursor.execute("""\
            SELECT value
              FROM query_term
             WHERE path = '/InScopeProtocol/FDAINDInfo/INDNumber'
               AND doc_id = ?""", docId)
        rows = docCursor.fetchall()
        indNumber = rows and rows[0][0] or u""
        personName = country = u""
        if p.pupLink:
            if p.pupLink not in pups:
                try:
                    pupId, pupFragId = p.pupLink.split('#')
                    pup = cdrdocobject.Person.Contact(pupId, pupFragId,
                                                      "Person Address Fragment "
                                                      "With Name")
                    pups[p.pupLink] = pup
                except Exception, e:
                    sys.stderr.write("PUP %s: %s\n" % (p.pupLink, e))
                    pups[p.pupLink] = None
            pup = pups[p.pupLink]
            if pup:
                country = pup.getCountry() or u""
                personName = pup.getAddressee() or u""
        row = sheet.addRow(rowNum, style)
        rowNum += 1
        row.addCell(1, docId)
        row.addCell(2, title, style)
        row.addCell(3, u"\n".join(p.designs), style)
        row.addCell(4, u"\n".join(p.phases), style)
        row.addCell(5, u"\n".join(p.studyTypes), style)
        row.addCell(6, u"\n".join(p.categories), style)
        row.addCell(7, u"\n".join(p.sources), style)
        row.addCell(8, personName, style)
        row.addCell(9, country)
        row.addCell(10, p.status)
        row.addCell(11, firstPub and firstPub[:10] or "")
        row.addCell(12, indNumber)
        sys.stderr.write("added CDR%d\n" % docId)
    row = cursor.fetchone()
fp = open('d:/Inetpub/wwwroot/Request4070-b.xls', 'wb')
book.write(fp, True)
fp.close()
