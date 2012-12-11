#----------------------------------------------------------------------
#
# $Id$
#
# Script to perform scheduled updates of electronic mailer tracking
# documents.
#
# BZIssue::4900 [support for GP mailers]
# BZIssue::4977 [fixed indentation bug at bottom of script]
#
#----------------------------------------------------------------------
import xml.dom.minidom, cdr, cdrmailcommon, time, lxml.etree as etree, urllib2

#----------------------------------------------------------------------
# Logging to mailer-specific logfile.
#----------------------------------------------------------------------
def logwrite(what):
    # print what
    cdr.logwrite(what, cdrmailcommon.LOGFILE)

#----------------------------------------------------------------------
# Object for a single document's mailer.
#----------------------------------------------------------------------
class Mailer:
    def __init__(self, id):
        self.id                = str(id)
        self.changesCategories = []
    def updateTracker(self, session, date=None):
        response = cdr.getDoc(session, int(self.id), 'Y', getObject = True)
        if type(response) in (type(""), type(u"")):
            logwrite("updateTracker(%s): %s" % (self.id, response))
            return False
        if self.alreadyUpdated(response.xml):
            logwrite("updateTracker(%s): already updated" % self.id)
            cdr.unlock(session, cdr.normalize(self.id),
                       reason = 'Tracker already updated')
            return True
        newDoc = self.transform(date)
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
    def transform(self, date=None):
        response = """\
 <Response>
  <Received>%s</Received>
""" % (date and date[:10] or time.strftime("%Y-%m-%d"))
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
session = cdr.login('etracker', '***REMOVED***')

#----------------------------------------------------------------------
# Update the row in the emailer server's database table for the mailer
# to reflect that the mailer response has been recorded in the CDR's
# tracking document.
#----------------------------------------------------------------------
def recordUpdate(mailerId, date):
    data = "mailerId=%s&recorded=%s" % (mailerId, str(date).replace(' ', '+'))
    fp = urllib2.urlopen("%s/recorded-gp.py" % cdr.emailerCgi(), data)
    response = fp.read()
    if not response.startswith('OK'):
        logwrite("mailer %s: %s" % (mailerId, response))

#----------------------------------------------------------------------
# Ask the emailer server to provide us with an XML report showing
# Genetics Professional mailers which have been completed.
#----------------------------------------------------------------------
fp = urllib2.urlopen("%s/completed-gp.py" % cdr.emailerCgi())
tree = etree.XML(fp.read())
nodes = [node for node in tree.findall('mailer')]

#----------------------------------------------------------------------
# For each mailer, update the CDR tracking document for the mailer
# with information about the response.
#----------------------------------------------------------------------
for node in nodes:
    mailer = Mailer(node.get('id'))
    if node.get('completed'):
        date = node.get('completed')
        if node.get('modified') == 'Y':
            mailer.changesCategories = ['Administrative changes']
        else:
            mailer.changesCategories = ['None']
    elif node.get('bounced'):
        mailer.changesCategories = ['Returned to sender']
        date = node.get('bounced')
    else:
        mailer.changesCategories = ['None']
        date = node.get('expired')
    if date:
        if mailer.updateTracker(session, date):
            recordUpdate(mailer.id, date)
cdr.logout(session)
