#----------------------------------------------------------------------
#
# $Id: Request1450.py,v 1.1 2005-01-20 00:04:31 bkline Exp $
#
# We need to add the following text "Eligibility criteria include the 
# following:" to all patient abstracts in Active, Temporarily Closed,
# and Active-Not-Yet-Approved trials, and make the phrase "Eligibility
# criteria" a glossary link.  The text is a para, and should go between
# the heading Eligibility and the itemized list of criteria:
# 
# Eligibility
# 
# Eligibility criteria include the following:
# 
#      - At least 18 years old
#      - More than 2 weeks since...
#
# Here is the exact text from a protocol document:
#
# <Para cdr:id="_35"><GlossaryTermRef cdr:href="CDR0000346518">Eligibility 
# criteria</GlossaryTermRef> include the following:</Para>
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdr, cdrdb, ModifyDocs, sys, re

#----------------------------------------------------------------------
# The Filter class is given to the ModifyDocs.Job object, which invokes
# the getDocIds() method to retrieve a list of CDR document IDs for
# processing.
#----------------------------------------------------------------------
class Filter:
    def getDocIds(self):
        conn = cdrdb.connect('CdrGuest')
        cursor = conn.cursor()
        cursor.execute("""\
    SELECT DISTINCT e.doc_id
               FROM query_term e
               JOIN query_term s
                 ON s.doc_id = e.doc_id
              WHERE e.path LIKE '/InScopeProtocol/ProtocolAbstract/Patient' +
                                '/EligibilityText%'
                AND s.path = '/InScopeProtocol/ProtocolAdminInfo' +
                             '/CurrentProtocolStatus'
                AND s.value IN ('Active', 'Temporarily closed',
                                'Approved-not yet active')
           ORDER BY e.doc_id""", timeout = 300)
        return [row[0] for row in cursor.fetchall()]

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
        self.pattern     = re.compile(r"<EligibilityText>\s*<ItemizedList")
        self.replacement = """\
<EligibilityText>
 <Para><GlossaryTermRef
  cdr:href="CDR0000346518">Eligibility criteria</GlossaryTermRef> """ + """\
include the following:</Para>
 <ItemizedList"""

    def run(self, docObj):
        return self.pattern.sub(self.replacement, docObj.xml)
if len(sys.argv) < 4 or sys.argv[3] not in ('test', 'live'):
    sys.stderr.write("usage: Request1450.py uid pwd test|live\n")
    sys.exit(1)
testMode = sys.argv[3] == 'test'
job = ModifyDocs.Job(sys.argv[1], sys.argv[2], Filter(), Transform(),
                     "Add eligibility criteria language (request #1450).",
                     testMode = testMode)
job.run()
