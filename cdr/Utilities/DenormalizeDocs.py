#----------------------------------------------------------------------
#
# $Id: DenormalizeDocs.py,v 1.2 2003-03-04 16:07:29 bkline Exp $
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2002/09/15 19:08:04  bkline
# New tools.
#
#----------------------------------------------------------------------
import sys, cdr, cdrdb

filters = {
    "InScopeProtocol": [
        "name:Denormalization Filter (1/1): InScope Protocol",
        "name:Denormalization: sort OrganizationName for Postal Address",
    ],
    "Organization": [
        "name:Denormalization Filter (1/1): Organization",
        "name:Denormalization: sort OrganizationName for Postal Address",
    ],
    "Person": [
        "name:Denormalization Filter (1/1): Person",
        "name:Denormalization: sort OrganizationName for Postal Address",
    ],
    "Term": [
        "name:Denormalization Filter (1/1): Terminology",
    ],
    "Summary": [
        "name:Denormalization Filter (1/5): Summary",
        "name:Denormalization Filter (2/5): Summary",
        "name:Denormalization Filter (3/5): Summary",
        "name:Denormalization Filter (4/5): Summary",
        "name:Denormalization Filter (5/5): Summary",
    ],
    "PoliticalSubUnit": [
        "name:Denormalization Filter (1/1): Political SubUnit",
        "name:Vendor Filter: PoliticalSubUnit"
    ],
    "StatMailer": [
        "name:InScopeProtocol Status and Participant Mailer"
    ],
}

maxDocs = -1
rows    = []
if len(sys.argv) < 2:
    sys.stderr.write("usage: DenormalizeDocs cdrType [max-docs]\n")
    sys.stderr.write("   or: DenormalizeDocs cdrType --list id [id ...]\n")
    sys.stderr.write("   or: DenormalizeDocs --filelist filename\n")
    sys.exit(1)
if sys.argv[1] == "--filelist":
    listFile = open(sys.argv[2])
    for line in listFile.readlines():
        line = line.strip()
        (id, docType) = line.split("\t")
        rows.append([int(id), docType])
else:
    cdrType = sys.argv[1]
    if not filters.has_key(cdrType):
        sys.stderr.write("don't know how to filter %s documents\n" % cdrType)
        sys.exit(1)
if len(sys.argv) > 2:
    if sys.argv[2] == '--list':
        for i in range(3, len(sys.argv)):
            rows.append([int(sys.argv[i]), cdrType])
    else:
        maxDocs = int(sys.argv[2])
if not rows:
    conn = cdrdb.connect()
    curs = conn.cursor()
    curs.execute("""\
    SELECT document.id, doc_type.name
      FROM document
      JOIN doc_type
        ON doc_type.id = document.doc_type
     WHERE doc_type.name = '%s'
       AND document.active_status = 'A'
  ORDER BY document.id""" % cdrType)
    rows = curs.fetchall()
sess = cdr.login('rmk', '***REDACTED***')
if maxDocs == -1: maxDocs = len(rows)
sys.stderr.write("found %d documents; processing %d\n" % (len(rows), maxDocs))
                 
numDocs = 0
for row in rows:
    if numDocs >= maxDocs:
        break
    numDocs += 1
    id = row[0]
    cdrType = row[1]
    if not filters.has_key(cdrType):
        sys.stderr.write("don't know how to filter %s documents\n" % cdrType)
        continue
    resp = cdr.filterDoc('guest', filters[cdrType], id)
    if type(resp) in (type(""), type(u"")):
        sys.stderr.write("Error for document %d: %s\n" % (id, resp))
    else:
        sys.stderr.write("Processing document CDR%010d\n" % id)
        open("%d.xml" % id, "w").write(resp[0])
