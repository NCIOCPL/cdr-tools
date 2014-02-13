#----------------------------------------------------------------------
#
# $Id$
#
# "We would like to create an ad hoc report for Wayne which he can use to
# record URLs of Cancer.gov pages that are related to dictionary terms. We
# would like the report to include every published term in the dictionary,
# but be organized by the glossary term concept (rather that the glossary
# term name) to avoid duplication. Please exclude blocked and/or unpublished
# terms from the report.
#
# The output should be in Excel.
#
# The columns (from left to right) in the report should be: CDR ID, Term
# Names, Page Title, PDQ Patient Summary URL, Drug Info Summary URL, Other
# URL.
#
# 1. The CDR ID should be the CDR ID of the Glossary Term Concept record.
# 2. The Term Names that are linked to each Concept should be listed in a
#    single cell in alphabetical order, separated by commas.
# 3. The report should be sorted alphabetically by first term name (after
#    step 2 is complete).
# 4. The last four columns should be blank. 
# 5. Please make the last 3 columns (which will contain URLs) much wider
#    than the others.
#
# We envision that this spreadsheet (once filled in) will eventually be used
# to populate RelatedExternalRef, RelatedSummaryRef, and
# RelatedDrugSummaryLink elements in the Glossary Term Concept records in
# the CDR.
#
# Thanks!
#
# BZIssue::4888
#
#----------------------------------------------------------------------
import cdrdb, ExcelWriter

class Concept:
    def __init__(self, docId, name):
        self.docId = docId
        self.names = [name]
    def __cmp__(self, other):
        diff = cmp(self.nameString, other.nameString)
        return diff or cmp(self.docId, other.docId)

concepts = {}
cursor = cdrdb.connect('CdrGuest').cursor()
cursor.execute("""\
    SELECT c.int_val, n.value
      FROM query_term c
      JOIN query_term n
        ON c.doc_id = n.doc_id
      JOIN pub_proc_cg p
        ON p.id = n.doc_id
     WHERE c.path = '/GlossaryTermName/GlossaryTermConcept/@cdr:ref'
       AND n.path = '/GlossaryTermName/TermName/TermNameString'""", timeout=300)
for docId, name in cursor.fetchall():
    if docId in concepts:
        concepts[docId].names.append(name)
    else:
        concepts[docId] = Concept(docId, name)
for docId in concepts:
    concept = concepts[docId]
    concept.names.sort()
    concept.nameString = u", ".join([n.strip() for n in concept.names])
concepts = concepts.values()
concepts.sort()
book = ExcelWriter.Workbook()
sheet = book.addWorksheet("Concepts")
sheet.addCol(1, 50)
sheet.addCol(2, 150)
sheet.addCol(3, 150)
sheet.addCol(4, 300)
sheet.addCol(5, 300)
sheet.addCol(6, 300)
font = ExcelWriter.Font(bold=True)
align = ExcelWriter.Alignment('Center', 'Center')
style = book.addStyle(alignment=align, font=font)
row = sheet.addRow(1, style=style)
row.addCell(1, "CDR ID", style=style)
row.addCell(2, "Term Names", style=style)
row.addCell(3, "Page Title", style=style)
row.addCell(4, "PDQ Patient Summary URL", style=style)
row.addCell(5, "Drug Info Summary URL", style=style)
row.addCell(6, "Other URL", style=style)
rowNum = 2
align = ExcelWriter.Alignment('Center', 'Top')
style1 = book.addStyle(alignment=align)
align = ExcelWriter.Alignment('Left', 'Top', wrap=True)
style2 = book.addStyle(alignment=align)
for concept in concepts:
    row = sheet.addRow(rowNum)
    rowNum += 1
    row.addCell(1, concept.docId, style=style1)
    row.addCell(2, concept.nameString, style=style2)
fp = open('d:/Inetpub/wwwroot/Request4888.xls', 'wb')
book.write(fp, True)
fp.close()
