#----------------------------------------------------------------------
# $Id$
#----------------------------------------------------------------------
import cdrdb, sys, cgi, cdr, datetime

GENPROF_HOST = 'mahler.nci.nih.gov'
DO_NOT_CONVERT = set([399, 400, 410, 401])
THRESHOLD = datetime.timedelta(seconds=2)
TESTING = True
TESTING = False
LOGFILE = 'd:/cdr/Log/ConvertGPMailers.log'

class Response:
    def __init__(self, when, comment, rts = False):
        self.when = when
        self.comment = comment
        self.rts = rts

def addPubJob(cursor, batch):
    #print batch[0].sent, batch[-1].sent
    cursor.execute("""\
        INSERT INTO pub_proc (pub_system, pub_subset, usr, output_dir,
                              started, completed, status, messages, email,
                              external, no_output)
             VALUES (176, 'Genetics Professional-Legacy mailer', 2, '',
                     ?, ?, 'Success', NULL, NULL, 'Y', 'Y')""",
                   (batch[0].sent, batch[-1].sent))
    cursor.execute("SELECT @@IDENTITY")
    return int(cursor.fetchall()[0][0])

def addPubProcDocRow(cursor, jobId, docId):
    cursor.execute("""\
        INSERT INTO pub_proc_doc (pub_proc, doc_id, doc_version, failure,
                                  messages, removed, subdir)
             VALUES (?, ?, 1, NULL, NULL, 'N', '')""", (jobId, docId))

class Mailer:
    def __init__(self, sent, mailerType, gpID, sentComment):
        self.sent = sent
        self.sentComment = sentComment
        self.mailerType = mailerType
        self.gpID = gpID
        self.cdrID = idMap.get(gpID, 0)
        self.responses = []
        if not self.cdrID:
            sys.stderr.write("GP %s was not converted\n" % self.gpID)
            self.docTitle = u"mailer for deleted GP %s" % self.gpID
        elif self.cdrID not in docTitles:
            row = cdr.getAllDocsRow(self.cdrID, conn)
            docTitles[self.cdrID] = self.docTitle = row['title']
        else:
            self.docTitle = docTitles[self.cdrID]
    def __cmp__(self, other):
        delta = cmp(self.sent, other.sent)
        if delta:
            return delta
        delta = cmp(self.cdrID, other.cdrID)
        if delta:
            return delta
        return cmp(self.gpID, other.gpID)
    def makeMailerTitle(self):
        name = self.docTitle.split(';')[0]
        docTitle = (u"%s [%s] [Genetics Professional-Legacy mailer]" %
                    (name, self.sent[:10]))
        return docTitle.encode('utf-8')
    def serialize(self, jobId):
        docTitle = cgi.escape(self.docTitle)
        x = [u"""\
<?xml version='1.0'?>
<Mailer xmlns:cdr='cips.nci.nih.gov/cdr'>
 <Type Mode='%s'>Genetics Professional-Legacy mailer</Type>
 <JobId>%d</JobId>
 <Recipient cdr:ref='CDR%010d'>%s</Recipient>
 <Document cdr:ref='CDR%010d'>%s</Document>
 <Sent>%s</Sent>
""" % (self.mailerType == 'E' and 'Web-based' or 'Mail', jobId,
       self.cdrID, docTitle, self.cdrID, docTitle, formatDate(self.sent))]
        for response in self.responses:
            x.append(u"""\
 <Response>
  <Received>%s</Received>
  <ChangesCategory>%s</ChangesCategory>
""" % (formatDate(response.when)[:10],
       response.rts and 'Returned to sender' or 'Legacy-no category'))
            comment = response.comment and response.comment.strip() or u""
            if comment:
                x.append(u"""\
  <Comment>%s</Comment>
""" % cgi.escape(comment))
            x.append(u"""\
 </Response>
""")
        comment = self.sentComment and self.sentComment.strip() or u""
        if comment:
            x.append(u"""\
 <Comment>%s</Comment>
""" % cgi.escape(comment))
        x.append(u"""\
</Mailer>
""")
        return u"".join(x)

conn = cursor = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
cursor.execute("""\
    SELECT doc_id, int_val
      FROM query_term
     WHERE path = '/Person/ProfessionalInformation'
                + '/GeneticsProfessionalDetails/LegacyGeneticsData/LegacyID'""")
def formatDate(d):
    if not d:
        return u""
    if len(d) > 10:
        return d[:10] + u"T" + d[11:19]
    return d

if TESTING:
    mailerId = 1
else:
    session = cdr.login('GPImport', '***REMOVED***')
    err = cdr.checkErr(session)
    if err:
        raise Exception(err)
idMap = {}
docTitles = {}
for cdrId, gpId in cursor.fetchall():
    idMap[gpId] = cdrId

cursor = cdrdb.connect(db='genprof', dataSource = GENPROF_HOST).cursor()
cursor.execute("""\
    SELECT h.SystemID, e.EventName, h.EventDate, h.Comments
      FROM testdu.tblHistory h
      JOIN testdu.lEvents e
        ON e.EventID = h.EventID
     WHERE e.EventName LIKE 'Verf%'
  ORDER BY h.EventDate""")
mailers = []
#latest  = { 'M': {}, 'E': {} }
latest = {}
for gpID, event, date, comment in cursor.fetchall():
    if gpID in DO_NOT_CONVERT:
        continue
    if gpID == 169: # duplicate of 312; see comment #143 of issue #4522
        gpID = 312
    if event.startswith('Verf_Sent_'):
        mailer = Mailer(date, event[-1].upper(), gpID, comment)
        mailers.append(mailer)
        latest[gpID] = mailer
    else:
        mailerType = event[-1]
        mailer = latest.get(gpID)
        if mailer is None:
            sys.stderr.write("ERROR: %s %s for GP%s; no mailer sent\n" %
                             (event, date, gpID))
            #continue
            # Arbitrarily using response date as date mailer was sent
            # (can't create row in pub_proc without a date)
            mailer = Mailer(date, event[-1].upper(), gpID,
                            u"Missing from legacy database; reconstructed"
                            u" by implication from response")
            mailers.append(mailer)
            latest[gpID] = mailer
        rts = event.startswith('Verf_Returned_')
        response = Response(date, comment, rts)
        mailer.responses.append(response)

def closeEnough(thisDate, prevDate):
    if prevDate is None:
        return False
    dt1 = datetime.datetime.strptime(prevDate, "%Y-%m-%d %H:%M:%S")
    dt2 = datetime.datetime.strptime(thisDate, "%Y-%m-%d %H:%M:%S")
    delta = dt2 - dt1
    return delta < THRESHOLD

mailers.sort()
mailerBatches = []
currentBatch = []
#lastMailer = None
lastDate = None
idsInBatch = set()
for mailer in mailers:
    if mailer.sentComment == 'Sent as part of a batch':
        if mailer.cdrID in idsInBatch:
            mailerBatches.append([mailer])
            idsInBatch = set([mailer.cdrID])
        elif closeEnough(mailer.sent, lastDate):
            mailerBatches[-1].append(mailer)
            if mailer.cdrID:
                idsInBatch.add(mailer.cdrID)
        else:
            mailerBatches.append([mailer])
            idsInBatch = set([mailer.cdrID])
        lastDate = mailer.sent
    else:
        mailerBatches.append([mailer])
        idsInBatch = set()
        lastDate = None
pubConn = cdrdb.connect()
pubCursor = pubConn.cursor()
for batch in mailerBatches:
    idsInBatch = set()
    jobId = addPubJob(pubCursor, batch)
    print "jobId is '%s' (type %s)" % (jobId, type(jobId))
    #print "Job %d has %d mailers" % (jobId, len(batch))
    for mailer in batch:
        mailerXml = mailer.serialize(jobId).encode('utf-8')
        if TESTING:
            fp = open('mailers/%05d.xml' % mailerId, 'w')
            fp.write(mailerXml)
            fp.close()
            mailerId += 1
        else:
            comment = 'converted from legacy genprof database'
            docTitle = mailer.makeMailerTitle()
            ctrl = { 'DocTitle': docTitle }
            doc = cdr.Doc(mailerXml, 'Mailer', ctrl=ctrl, encoding='utf-8')
            docId, warnings = cdr.addDoc(session, doc=str(doc), comment=comment,
                                         val='Y', reason=comment, ver='Y',
                                         verPublishable='N', showWarnings='Y')
            if not docId:
                cdr.logwrite("failure adding mailer %s" % docTitle, LOGFILE)
            else:
                cdr.logwrite("added %s (%s)" % (docId, docTitle), LOGFILE)
                cdr.unlock(session, docId)
            if warnings:
                if type(warnings) in (str, unicode):
                    cdr.logwrite(warnings, LOGFILE)
                else:
                    for warning in warnings:
                        cdr.logwrite(warning, LOGFILE)
        if mailer.cdrID:
            if mailer.cdrID in idsInBatch:
                sys.stderr.write("already published %d in job %d (%s)\n" %
                                 (mailer.cdrID, jobId, mailer.sent))
            else:
                addPubProcDocRow(pubCursor, jobId, mailer.cdrID)
                idsInBatch.add(mailer.cdrID)
    pubConn.commit()
