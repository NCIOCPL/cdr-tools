#----------------------------------------------------------------------
#
# $Id$
#
# Script to show information extracted from cancer.gov HTML pages.
#
# BZIssue::4835
#
#----------------------------------------------------------------------
import cdrdb, lxml.etree as etree, cgi

fp = open('d:/tmp/pdq-board-member-name-deltas.txt', 'w')
def getPersonName(docId):
    cursor.execute("SELECT xml FROM document WHERE id = ?", docId)
    doc = cursor.fetchall()[0][0]
    tree = etree.XML(doc.encode('utf-8'))
    forename = surname = middle = u""
    suffixes = []
    for node in tree.findall('PersonNameInformation'):
        for child in node.findall('GivenName'):
            forename = child.text
        for child in node.findall('SurName'):
            surname = child.text
        for child in node.findall('MiddleInitial'):
            middle = child.text
        for child in node.findall('ProfessionalSuffix'):
            for grandchild in child:
                if grandchild.tag in ('StandardProfessionalSuffix',
                                      'CustomProfessionalSuffix'):
                    suffixes.append(grandchild.text.strip())
    name = u"%s %s" % (forename.strip(), middle.strip())
    name = (u"%s %s" % (name.strip(), surname.strip())).strip()
    if suffixes:
        name = u"%s, %s" % (name, u", ".join(suffixes))
    return name.encode('utf-8'), "%s|%s|%s" % (surname.strip().upper(),
                                               forename.strip().upper(),
                                               middle.strip().upper())
                             
class Member:
    def __cmp__(self, other):
        return cmp(self.key, other.key)
    def __init__(self, node):
        self.personId = node.get('person-id')
        self.boardMemberId = node.get('board-member-id')
        self.name, self.key = getPersonName(self.personId)
        self.board = self.affiliation = None
        self.docName = None
        affiliations = []
        for child in node:
            if child.tag == 'PDQBoardMemberName':
                self.docName = child.text
                if self.docName != self.name.split(',')[0]:
                    fp.write("cancer.gov has '%s' where CDR has '%s'\n" %
                             (self.docName, self.name.split(',')[0]))
            elif child.tag == 'PDQBoard':
                self.board = child.text
            elif child.tag == 'Affiliations':
                for grandchild in child:
                    if grandchild.tag == 'Affiliation':
                        if grandchild.get('Usage') != 'BD':
                            lines = []
                            for line in grandchild:
                                if line.tag == 'AffiliationName':
                                    lines.append(line.text)
                            affiliations.append(", ".join(lines))
        self.affiliation = " & ".join(affiliations)
cursor = cdrdb.connect('CdrGuest').cursor()
doc = open('d:/Inetpub/wwwroot/PDQBoardMembers.xml').read()
tree = etree.XML(doc)
boards = {}
for node in tree.findall('PDQBoardMember'):
    member = Member(node)
    if member.board not in boards:
        boards[member.board] = []
    boards[member.board].append(member)
print """\
<html>
 <head>
  <title>Summary Reviewers</title>
  <style type='text/css'>
   * { font-family: Arial, sans-serif; }
   h1 { font-size: 16pt; color: green; }
  </style>
 </head>
 <body>"""
keys = boards.keys()
keys.sort()
for board in keys:
    print """\
  <h1>%s</h1>
  <ul>""" % board
    members = boards[board]
    members.sort()
    for member in members:
        if member.affiliation:
            print "   <li>%s (%s)</li>" % (cgi.escape(member.name),
                                           cgi.escape(member.affiliation))
        else:
            print "   <li>%s</li>" % cgi.escape(member.name)
    print "  </ul>"
print """\
 </body>
</html>"""
fp.close()
