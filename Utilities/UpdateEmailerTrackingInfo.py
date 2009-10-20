#----------------------------------------------------------------------
#
# $Id$
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2004/06/19 12:30:44  bkline
# Script to perform scheduled updates of electronic mailer tracking
# documents.
#
#----------------------------------------------------------------------
import xml.dom.minidom, sys, cdr, cdrmailcommon, time

#----------------------------------------------------------------------
# Logging to mailer-specific logfile.
#----------------------------------------------------------------------
def logwrite(what):
    # print what
    cdr.logwrite(what, cdrmailcommon.LOGFILE)

#----------------------------------------------------------------------
# Object for a batch of mailers.
#----------------------------------------------------------------------
class MailerBatch:
    def __init__(self, id):
        self.id      = id
        self.mailers = {}
    def updateTrackers(self, conn, cursor, session):
        failures = 0
        for key in self.mailers:
            if not self.mailers[key].updateTracker(session):
                failures += 1
        if failures:
            logwrite("updateTrackers(): batch %s not updated" % self.id)
        else:
            logwrite("updateTrackers(): batch %s complete" % self.id)
            #return True
            cursor.execute("""\
                UPDATE emailer_batch
                   SET updated = NOW()
                 WHERE recip = %s""", self.id)
            conn.commit()

#----------------------------------------------------------------------
# Object for a single document's mailer.
#----------------------------------------------------------------------
class Mailer:
    def __init__(self, id):
        self.id                = id
        self.changesCategories = []
    def updateTracker(self, session):
        response = cdr.getDoc(session, int(self.id), 'Y', getObject = 1)
        if type(response) in (type(""), type(u"")):
            logwrite("updateTracker(%s): %s" % (self.id, response))
            return False
        if self.alreadyUpdated(response.xml):
            logwrite("updateTracker(%s): already updated" % self.id)
            cdr.unlock(session, cdr.normalize(self.id),
                       reason = 'Tracker already updated')
            return True
        newDoc = self.transform()
        if not newDoc:
            cdr.unlock(session, cdr.normalize(self.id),
                       reason = 'Unable to filter document')
            return False
        response.xml = newDoc
        doc = str(response)
        file = open("tracker/tracker-%s.xml" % self.id, "w")
        file.write(doc)
        file.close()
        cmt = "Automatic update of electronic mailer tracking document"
        response = cdr.repDoc(session, doc = doc, comment = cmt,
                              checkIn = 'Y', val = 'Y', reason = cmt,
                              ver = 'Y', showWarnings = 1)
        if response[1]:
            logwrite("updateTracker(%s): %s" % (self.id, response[1]))
        if not response[0]:
            return False
        logwrite("updated tracking document %s" % self.id)
        return True
    def alreadyUpdated(self, docXml):
        docElem = xml.dom.minidom.parseString(docXml).documentElement
        for child in docElem.childNodes:
            if child.nodeName == 'Response':
                return True
        return False
    def transform(self):
        response = """\
 <Response>
  <Received>%s</Received>
""" % time.strftime("%Y-%m-%d")
        for changesCategory in self.changesCategories:
            response += """\
  <ChangesCategory>%s</ChangesCategory>
""" % changesCategory
        response += " </Response>"
        filter = """\
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

 <!-- Stick in the new Response element at end of Mailer. -->
 <xsl:template                  match = 'Mailer'>
  <Mailer>
   <xsl:apply-templates        select = '@*|node()|comment()|
                                         processing-instruction()'/>
   <xsl:if                       test = 'not(Response)'>
%s
   </xsl:if>
  </Mailer>
 </xsl:template>
</xsl:transform>
""" % response
        response = cdr.filterDoc('guest', filter, int(self.id), inline = 1)
        if type(response) in (type(''), type(u"")):
            logwrite('MailerTracker.transform(%s): %s' % (self.id, response))
            return None
        if response[1]:
            logwrite('MailerTracker.transform(%s): WARNING: %s' %
                     (self.id, response[1]))
        return response[0]
        
#----------------------------------------------------------------------
# Retrieve the tracking information from the emailer's dropbox database.
#----------------------------------------------------------------------
#logwrite('UpdateEmailerTrackingInfo')
conn = cdrmailcommon.emailerConn('dropbox')
cursor = conn.cursor()
cursor.execute("""\
    SELECT d.doc, c.name, b.recip
      FROM doc_changes_category d
      JOIN emailer_batch b
        ON b.recip = d.recip
      JOIN changes_category c
        ON c.id = d.category
     WHERE b.reported IS NOT NULL
       AND b.updated IS NULL""")
rows = cursor.fetchall()
batches = {}
for doc, category, recip in rows:
    if not recip in batches:
        batch = batches[recip] = MailerBatch(recip)
    else:
        batch = batches[recip]
    if doc not in batch.mailers:
        mailer = batch.mailers[doc] = Mailer(doc)
    else:
        mailer = batch.mailers[doc]
    mailer.changesCategories.append(category)
session = cdr.login('etracker', '***REMOVED***')
for key in batches:
    batches[key].updateTrackers(conn, cursor, session)
cdr.logout(session)
