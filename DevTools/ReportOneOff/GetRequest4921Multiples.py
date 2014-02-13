import ExcelReader, ExcelWriter

def get(row, i):
    try:
        val = row[i].val
        if val == 'NULL':
            return None
        return val
    except:
        return None

book = ExcelReader.Workbook(r"\\franck\d$\tmp\glossary-links.xls")
sheet = book[0]
concepts = {}
for row in sheet:
    try:
        values = [get(row, i) for i in range(12)]
        cdrId = int(values[0])
        if cdrId not in concepts:
            concepts[cdrId] = []
        concepts[cdrId].append(values)
    except:
        print "skipping", row[0].val
        continue
multiples = []
for cdrId in concepts:
    if len(concepts[cdrId]) > 1:
           multiples.append(cdrId)
multiples.sort()
book = ExcelWriter.Workbook()
sheet = book.addWorksheet('Multiples')
rowNumber = 1
for cdrId in multiples:
    for values in concepts[cdrId]:
        row = sheet.addRow(rowNumber)
        colNumber = 1
        for v in values:
            if v is not None:
                row.addCell(colNumber, v)
            colNumber += 1
        rowNumber += 1
fp = open('d:/Inetpub/wwwroot/Request4921Multiples.xls', 'wb')
book.write(fp, True)
fp.close()
