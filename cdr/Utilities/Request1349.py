#----------------------------------------------------------------------
#
# $Id: Request1349.py,v 1.3 2004-12-10 12:45:49 bkline Exp $
#
# [Kim]
# Attempting to summarize Friday's decisions. Most of this is reflected 
# in the issues.
#
# Web-based mailers - Cooperative Groups (Issue 1349)
# *  One-off global to add update mode (S&P Check) to RSS data for all
#    cooperative groups in the hard coded list (Bob)
# [this supercedes the request below from Lakshmi]
#
# [Lakshmi]
# Actually after thinking a little more about this, I was wondering why
# we should not remove the PUP role altogether if the person has more
# than one role and also remove the Person link altogether. What do you
# think? I don't think we have any special validation that requires the
# presence of the Update Person role
#
# There are two possible data scenarios here:
#
# 1. One LeadOrgPersonnel element with two PersonRole elements with values 
# of "Protocol Chair" or "Prinicipal Investigator" and "Update Person".
#
# 2. Two LeadOrgPersonnel elements -- one with PersonRole of Update Person and 
# another with PersonRole of Protocol Chair or Prinicpal Investigator.
#
# In the first scenario, we would take out the LeadOrgPersonnel/PersonRole 
# element with value of Update Person. This would leave the 
# LeadOrgPersonnel/Person and the PersonRole element in tact -- no validity 
# issues.
#
# In the second scenario, we would take out the LeadOrgPerson block where the 
# PersonRole element had the value Update Person. In this case there would be 
# another LeadOrgPersonnel block that would still be there -- not validity
# issues.
#
# If it finds a lead org that only has one lead org person, and that
# person has only one role, and that role is "Update Person" then
# the program would do nothing. I don't think we will encounter 
# that use case (unless the protocol is midway through being processed).
# Can the program report these instances? CIAT can then fix manually.
#
# $Log: not supported by cvs2svn $
# Revision 1.2  2004/10/12 13:21:44  bkline
# Users decided to add RSS UpdateMode elements instead of stripping PUPs.
#
# Revision 1.1  2004/10/11 12:40:46  bkline
# Suppress mailers for NCI Cooperative groups that will be updated from
# RSS data.
#
#----------------------------------------------------------------------
import cdr, cdrdb, ModifyDocs, sys, xml.sax

#----------------------------------------------------------------------
# The Filter class is given to the ModifyDocs.Job object, which invokes
# the getDocIds() method to retrieve a list of CDR document IDs for
# processing.
#----------------------------------------------------------------------
class Filter:
    def getDocIds(self):
        ids = {}
        conn = cdrdb.connect('CdrGuest')
        cursor = conn.cursor()
        cursor.execute("""\
SELECT DISTINCT q.doc_id
           FROM query_term q
           JOIN doc_version v
             ON v.id = q.doc_id
          WHERE q.int_val IN (32676, 30265, 35676, 36120,
                              36176, 35709, 36149, 35883)
            AND q.path = '/InScopeProtocol/ProtocolAdminInfo'
                       + '/ProtocolLeadOrg/LeadOrganizationID/@cdr:ref'
            AND v.publishable = 'Y'""")
        for row in cursor.fetchall():
            ids[row[0]] = 1
        cursor.execute("""\
SELECT DISTINCT q.doc_id
           FROM query_term q
           JOIN ready_for_review r
             ON r.doc_id = q.doc_id
          WHERE q.int_val IN (32676, 30265, 35676, 36120,
                              36176, 35709, 36149, 35883)
            AND q.path = '/InScopeProtocol/ProtocolAdminInfo'
                       + '/ProtocolLeadOrg/LeadOrganizationID/@cdr:ref'""")
        for row in cursor.fetchall():
            ids[row[0]] = 1
        keys = ids.keys()
        keys.sort()
        return keys

class UpdateModeHandler(xml.sax.handler.ContentHandler):
    
    nciCoopGroups = { 32676: True,
                      30265: True,
                      35676: True,
                      36120: True,
                      36176: True,
                      35709: True,
                      36149: True,
                      35883: True }

    def __init__(self):
        self.docStrings         = []
        self.hasSandPUpdateMode = False
        self.inSandPUpdateMode  = False
        self.changed            = False
        self.oldValue           = u""
        self.inNciCoopGroup     = False
    
    def startDocument(self):
        self.docStrings         = [u"<?xml version='1.0'?>\n"]
        self.hasSandPUpdateMode = False
        self.inSandPUpdateMode  = False
        self.changed            = False
        self.oldValue           = u""
        self.inNciCoopGroup     = False
        self.droppingElements   = False

    def startElement(self, name, attributes):
        if name == u'ProtocolLeadOrg':
            self.hasSandPUpdateMode = False
            self.inNciCoopGroup = False
            self.droppingElements = False
        elif name == u"LeadOrganizationID":
            orgId = attributes.getValue('cdr:ref')
            if orgId:
                orgId = cdr.exNormalize(orgId)[1]
                if orgId in UpdateModeHandler.nciCoopGroups:
                    self.inNciCoopGroup = True
        elif name == u'UpdateMode':
            if self.inNciCoopGroup:
                if attributes.getValue('MailerType') == 'Protocol_SandP':
                    self.hasSandPUpdateMode = True
                    self.inSandPUpdateMode = True
                    self.oldValue = u""
        elif name == u"ProtocolSites" and self.inNciCoopGroup == True:
            self.droppingElements = False # True to turn this back on
        if not self.droppingElements:
            self.docStrings.append(u"<%s" % name)
            for attrName in attributes.getNames():
                val = xml.sax.saxutils.quoteattr(attributes.getValue(attrName))
                self.docStrings.append(u" %s=%s" % (attrName, val))
            self.docStrings.append(u">")
    def endElement(self, name):
        if name == 'ProtocolLeadOrg':
            if self.inNciCoopGroup and not self.hasSandPUpdateMode:
                self.docStrings.append(u'<UpdateMode MailerType='
                                       u'"Protocol_SandP">RSS</UpdateMode>')
                self.changed = True
            self.inNciCoopGroup = False
        if self.inSandPUpdateMode:
            if self.inNciCoopGroup:
                self.docStrings.append(u"RSS")
                if self.oldValue != u"RSS":
                    self.changed = True
            self.inSandPUpdateMode = False
        if not self.droppingElements:
            self.docStrings.append(u"</%s>" % name)
        elif name == u"ProtocolSites":
            self.droppingElements = False
    def characters(self, content):
        if not self.droppingElements:
            if self.inNciCoopGroup and self.inSandPUpdateMode:
                self.oldValue += content
            else:
                self.docStrings.append(xml.sax.saxutils.escape(content))
    def processingInstruction(self, target, data):
        if not self.droppingElements:
            self.docStrings.append(u"<?%s %s?>" % (target, data))

#----------------------------------------------------------------------
# The Transform class is given to the ModifyDocs.Job object, which in
# turn gives it to each ModifyDocs.Doc object.  The run() method of
# this class takes a cdr.Doc object and returns a (possibly) modified
# copy of that object's xml member.
#
# See comment at top for this job's logic.
#----------------------------------------------------------------------
class Transform:
    def __init__(self):
        self.parser = UpdateModeHandler()
    def run(self, docObj):
        xml.sax.parseString(docObj.xml, self.parser)
        if self.parser.changed:
            return u"".join(self.parser.docStrings).encode('utf-8')
        else:
            return docObj.xml

job = ModifyDocs.Job(sys.argv[1], sys.argv[2], Filter(), Transform(),
                     "Add RSS update mode (request #1349).", testMode = False)
job.run()
