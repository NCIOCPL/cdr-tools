#----------------------------------------------------------------------
#
# $Id: DownloadCTGovProtocols.py,v 1.2 2003-12-14 19:07:06 bkline Exp $
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2003/11/26 13:01:20  bkline
# Nightly job to pull down the latest set of cancer trials from
# ClinicalTrials.gov.
#
#----------------------------------------------------------------------
import cdr, zipfile, re, xml.dom.minidom, sys, urllib, cdrdb, os, time

def log(what):
    sys.stderr.write(what)
    sys.stdout.write(what)

def loadDispositions(cursor):
    dispNames = {}
    dispCodes = {}
    cursor.execute("SELECT id, name FROM ctgov_disposition")
    for row in cursor.fetchall():
        dispNames[row[0]] = row[1]
        dispCodes[row[1]] = row[0]
    return [dispNames, dispCodes]

def normalizeXml(doc):
    response = cdr.filterDoc('guest',
                             ['name:Normalize NLM CTGovProtocol document'],
                             doc = doc)
    if type(response) in (type(""), type(u"")):
        raise Exception(response)
    return response[0]

def compareXml(a, b):
    return cmp(normalizeXml(a), normalizeXml(b))

class Doc:
    def __init__(self, xmlFile, name):
        self.name          = name
        self.xmlFile       = xmlFile
        self.dom           = xml.dom.minidom.parseString(xmlFile)
        self.officialTitle = None
        self.briefTitle    = None
        self.nlmId         = None
        self.orgStudyId    = None
        self.title         = None
        self.status        = None
        self.nciSponsored  = 0
        self.verified      = None
        self.lastChanged   = None
        self.cdrId         = None
        self.disposition   = None
        self.oldXml        = None
        for node in self.dom.documentElement.childNodes:
            if node.nodeName == "id_info":
                for child in node.childNodes:
                    if child.nodeName == "org_study_id":
                        self.orgStudyId = cdr.getTextContent(child).strip()
                    elif child.nodeName == "nct_id":
                        self.nlmId = cdr.getTextContent(child).strip()
            elif node.nodeName == "brief_title":
                self.briefTitle = cdr.getTextContent(node).strip()
            elif node.nodeName == "official_title":
                self.officialTitle = cdr.getTextContent(node).strip()
            elif node.nodeName == "sponsors":
                for child in node.getElementsByTagName("agency"):
                    name = cdr.getTextContent(node).strip().upper()
                    if name == "NATIONAL CANCER INSTITUTE (NCI)":
                        self.nciSponsored = 1
                        break
            elif node.nodeName == "overall_status":
                self.status = cdr.getTextContent(node).strip()
            elif node.nodeName == "verification_date":
                self.verified = cdr.getTextContent(node).strip()
            elif node.nodeName == "lastchanged_date":
                self.lastChanged = cdr.getTextContent(node).strip()
        self.title = self.officialTitle or self.briefTitle
        if self.nlmId:
            row = None
            try:
                cursor.execute("""\
            SELECT xml, cdr_id, disposition
              FROM ctgov_import
             WHERE nlm_id = ?""", self.nlmId)
                row = cursor.fetchone()
            except Exception, e:
                log("Failure selecting from ctgov_import for %s\n"
                    % self.nlmId)
                sys.exit(1)
            if row:
                self.oldXml, self.cdrId, self.disposition = row

#----------------------------------------------------------------------
# Seed the table with documents we know to be duplicates.
#----------------------------------------------------------------------
conn = cdrdb.connect()
cursor = conn.cursor()
dispNames, dispCodes = loadDispositions(cursor)
expr = re.compile(r"CDR0*(\d+)\s+(NCT\d+)\s*")
for line in open('ctgov-dups.txt'):
    match = expr.match(line)
    if match:
        cdrId, nlmId = match.groups()
        cdrId = int(cdrId)
        cursor.execute("""\
            SELECT cdr_id, disposition
              FROM ctgov_import
             WHERE nlm_id = ?""", nlmId)
        row = cursor.fetchone()
        if row:
            if row[0] != dispCodes['duplicate']:
                if row[0] == dispCodes['imported']:
                    log('duplicate %s already imported as CDR%d\n' %
                        (nlmId, row[1]))
                else:
                    try:
                        cursor.execute("""\
                    UPDATE ctgov_import
                       SET disposition = ?,
                           dt = GETDATE(),
                           cdr_id = ?,
                           comment = 'Marked as duplicate by download job'
                     WHERE nlm_id = ?""", (dispCodes['duplicate'],
                                           cdrId,
                                           nlmId))
                        conn.commit()
                    except:
                        log('Unable to update row for %s/CDR%d\n' %
                            (nlmId, cdrId))
        else:
            try:
                cursor.execute("""\
            INSERT INTO ctgov_import (nlm_id, cdr_id, disposition, dt,
                                      comment)
                 VALUES (?, ?, ?, GETDATE(),
                         'Marked as duplicate by download job')""",
                           (nlmId, cdrId, dispCodes['duplicate']))
                conn.commit()
            except:
                log('Unable to insert row for %s/CDR%d\n' %
                    (nlmId, cdrId))
                         
if len(sys.argv) > 1:
    name = sys.argv[1]
else:
    url     = "http://clinicaltrials.gov/search/condition=cancer?studyxml=true"
    urlobj  = urllib.urlopen(url)
    page    = urlobj.read()
    name    = time.strftime("CTGovDownload-%Y%m%d%H%M%S.zip")
    zipFile = open(name, "wb")
    zipFile.write(page)
    zipFile.close()
    log("Trials downloaded to %s\n" % name)
file = zipfile.ZipFile(name)
nameList = file.namelist()
tally = [0, 0]
added = 0
updated = 0
for name in nameList: #['NCT00050011.xml']: #nameList:
    wanted = 0
    xmlFile = file.read(name)
    doc = Doc(xmlFile, name)
    if not doc.nlmId:
        log("Skipping document without NLM ID\n")
    elif not doc.title:
        log("Skipping %s, which has no title\n" % doc.nlmId)
    #elif doc.nciSponsored:
    #    log("Skipping %s, which is NCI sponsored\n" % doc.nlmId)
    elif not doc.cdrId and doc.orgStudyId and doc.orgStudyId.startswith("CDR"):
        log("Skipping %s, which has a CDR ID\n" % doc.nlmId)
    elif not doc.cdrId and (not doc.status or
                            doc.status.upper() not in ("RECRUITING",
                                                       "NOT YET RECRUITING")):
        log("Skipping %s, which has a status of %s\n" % (doc.nlmId,
                                                         doc.status))
    elif doc.disposition:
        disp = doc.disposition
        dispName = dispNames[disp]
        if dispName in ('out of scope', 'duplicate'):
            log("Skipping %s, disposition is %s\n" % (doc.nlmId, dispName))
            tally[0] += 1
            continue
        elif dispName == 'imported':
            if not compareXml(doc.oldXml, doc.xmlFile):
                log("Skipping %s (already imported, unchanged at NLM)\n"
                    % doc.nlmId)
                tally[0] += 1
                continue
            else:
                disp = dispCodes['import requested']
        try:
            cursor.execute("""\
                UPDATE ctgov_import
                   SET title = ?,
                       xml = ?,
                       downloaded = GETDATE(),
                       disposition = ?,
                       dt = GETDATE(),
                       verified = ?,
                       changed = ?
                 WHERE nlm_id = ?""",
                           (doc.title[:255],
                            doc.xmlFile,
                            disp,
                            doc.verified,
                            doc.lastChanged,
                            doc.nlmId))
            conn.commit()
            wanted = 1
            updated += 1
            log("Updated %s with disposition %s\n" % (doc.nlmId,
                                                      dispNames[disp]))
        except Exception, info:
            log("Failure updating %s: %s\n" % (doc.nlmId, str(info)))
    else:
        disp = dispCodes['not yet reviewed']
        try:
            cursor.execute("""\
        INSERT INTO ctgov_import (nlm_id, title, xml, downloaded,
                                  disposition, dt, verified, changed)
             VALUES (?, ?, ?, GETDATE(), ?, GETDATE(), ?, ?)""",
                           (doc.nlmId,
                            doc.title[:255],
                            doc.xmlFile,
                            disp,
                            doc.verified,
                            doc.lastChanged))
            conn.commit()
            wanted = 1
            added += 1
            log("Added %s with disposition %s\n" % (doc.nlmId,
                                                    dispNames[disp]))
        except Exception, info:
            log("Failure importing %s: %s\n" % (doc.nlmId, str(info)))
    tally[wanted] += 1

log("Added %d; updated %d; skipped %d\n" % (added, updated, tally[0]))
