#----------------------------------------------------------------------
#
# $Id$
#
# Generate documents in the following form:
#  <PDQBoardMemberInfo>
#   <BoardMemberName cdr:ref='CDR0000999999'/>
#   <BoardMemberContact>
#    <PersonContactID>_F1</PersonContactID>
#   </BoardMemberContact>
#   <BoardMemberContactMode>FedEx</BoardMemberContactMode>
#   <BoardMembershipDetails>
#    <BoardName cdr:ref='CDR000088888888'/>
#    <CurrentMember>Yes</CurrentMember>
#    <InvitationDate>2004-01-01</InvitationDate>
#    <ResponseToInvitation>Accepted</ResponseToInvitation>
#   </BoardMembershipDetails>
#   <BoardMembershipDetails>....
#  </PDQBoardMemberInfo>
#
# BZIssue::1044
#
#----------------------------------------------------------------------
import cdr, cdrdb, sys

def mapBoardType(path):
    path = path.upper()
    if path.find('PDQEDITORIALBOARD') != -1:
        return "PDQ Editorial Board"
    elif path.find('PDQADVISORYBOARD') != -1:
        return "PDQ Advisory Board"
    else:
        return "PDQ Volunteer Advisory Board"

def wrapDoc(doc):
    return """\
<CdrDoc Type='PDQBoardMemberInfo'>
 <CdrDocCtl>
  <DocComment>Generated from Person document</DocComment>
 </CdrDocCtl>
 <CdrDocXml><![CDATA[%s]]></CdrDocXml>
</CdrDoc>
""" % doc.encode("utf-8")

session = cdr.login(sys.argv[1], sys.argv[2])
conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
cursor.execute("""\
         SELECT q1.doc_id, q1.int_val, q1.path, q2.value
           FROM query_term q1
LEFT OUTER JOIN query_term q2
             ON q2.doc_id = q1.doc_id
          WHERE q1.path IN (
                    '/Person/ProfessionalInformation' +
                    '/PDQBoardMembershipDetails/PDQEditorialBoard/@cdr:ref',
                    '/Person/ProfessionalInformation' +
                    '/PDQBoardMembershipDetails/PDQAdvisoryBoard/@cdr:ref',
                    '/Person/ProfessionalInformation' +
                    '/PDQBoardMembershipDetails/PDQVolunteerAdvisoryBoard' +
                    '/@cdr:ref')
            AND q2.path = '/Person/PersonLocations/CIPSContact'""",
               timeout = 500)

class Board:
    def __init__(self, id, path):
        self.id = id
        self.type = mapBoardType(path)

class BoardMember:
    def __init__(self, id, cipsContact):
        self.id          = id
        self.cipsContact = cipsContact
        self.boards      = []
boards       = {}
boardMembers = {}
for id, board, path, cipsContact in cursor.fetchall():
    if not boardMembers.has_key(id):
        boardMember = boardMembers[id] = BoardMember(id, cipsContact)
    else:
        boardMember = boardMembers[id]
    boardMember.boards.append(Board(board, path))
for id in boardMembers:
    memb = boardMembers[id]
    doc  = u"""\
<?xml version='1.0' encoding='UTF-8'?>
<PDQBoardMemberInfo xmlns:cdr='cips.nci.nih.gov/cdr'>
 <BoardMemberName cdr:ref='CDR%010d'/>
 <BoardMemberContact>
  <PersonContactID>%s</PersonContactID>
 </BoardMemberContact>
 <BoardMemberContactMode>FedEx</BoardMemberContactMode>
 <BoardMemberAssistant>
  <AssistantName><?xm-replace_text {Enter an assistant name (required)}?></AssistantName>
  <AssistantPhone Public='No'><?xm-replace_text {Enter a phone number (required)}?></AssistantPhone>
  <AssistantFax><?xm-replace_text {Optionally enter a fax number}?></AssistantFax>
  <AssistantEmail Public="No"><?xm-replace_text {Optionally enter an email address}?></AssistantEmail>
 </BoardMemberAssistant>
""" % (id, memb.cipsContact or u"")
    for board in memb.boards:
        doc += u"""\
 <BoardMembershipDetails>
  <BoardName cdr:ref='CDR%010d'/>
  <CurrentMember>Yes</CurrentMember>
  <InvitationDate>0000-00-00</InvitationDate>
  <ResponseToInvitation>Accepted</ResponseToInvitation>
  <TermStartDate><?xm-replace_text {Optionally enter start date for membership term}?></TermStartDate>
  <TermRenewalFrequency><?xm-replace_text {Optionally select frequency of term renewal}?></TermRenewalFrequency>
  <AreaOfExpertise><?xm-replace_text {Optionally select an area of expertise}?></AreaOfExpertise>
 </BoardMembershipDetails>
""" % board.id
    doc += """\
</PDQBoardMemberInfo>
"""
    response = cdr.addDoc(session, doc = wrapDoc(doc),
                          comment = 'Generated from Person document')
    errors = cdr.getErrors(response, errorsExpected = 0, asSequence = 1)
    if errors:
        print str(errors)
    else:
        cdr.unlock(session, response,
                   reason = 'checking in generated document')
        print response
