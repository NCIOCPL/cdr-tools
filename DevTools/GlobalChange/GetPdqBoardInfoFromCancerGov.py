#----------------------------------------------------------------------
#
# $Id$
#
# Script for scraping board member information from cancer.gov HTML pages.
#
# BZIssue::4835
#
#----------------------------------------------------------------------
import re, urllib, cdrdb

cursor = cdrdb.connect('CdrGuest').cursor()
cursor.execute("""\
    SELECT d.id, q.doc_id, d.title
      FROM document d
      JOIN query_term q
        ON d.id = q.int_val
     WHERE q.path = '/PDQBoardMemberInfo/BoardMemberName/@cdr:ref'""")
members = {}
for personId, memberId, title in cursor.fetchall():
    name = title.split(';')[0].strip()
    if name == 'Inactive':
        name = title.split(';')[1].strip()
    try:
        last, first = name.split(',')
    except Exception, e:
        print personId, memberId, title
        raise
    key = ("%s %s" % (first.split()[0], last.strip())).upper()
    if key in members:
        raise Exception("too many documents for '%s'" % key)
    members[key] = (personId, memberId)
members['A. RITCHEY'] = (25488, 369928)
members['MICHAEL QUAGLIA'] = (9475, 391186)
members['DOUGLAS KINGHORN'] = (453610, 453613)
boards = { 'adult-treatment': 'Adult Treatment',
           'pediatric-treatment': 'Pediatric Treatment',
           'supportive-care': 'Supportive Care',
           'screening-prevention': 'Screening and Prevention',
           'cancer-genetics': 'Genetics',
           'cancer-cam': 'Complementary and Alternative Medicine' }
standard = open('d:/tmp/task4835-standard.txt', 'w')
exceptions = open('d:/tmp/task4835-exceptions.txt', 'w')
pattern = re.compile('<li><strong>([^<]+)</strong>(.*?)</li>', re.DOTALL)
specials = {
    'DOUGLAS ARTHUR': """\
  <Affiliations>
   <Affiliation>
    <AffiliationName>Medical College of Virginia Hospital</AffiliationName>
    <AffiliationName>Virginia Commonwealth University</AffiliationName>
    <AffiliationPlace>Richmond, VA</AffiliationPlace>
   </Affiliation>
  </Affiliations>""",
    'JANET DANCEY': """\
  <Affiliations>
   <Affiliation Usage='BD'>
    <AffiliationName>Ontario Institute for Cancer Research</AffiliationName>
    <AffiliationPlace>Toronto, Ontario, Canada</AffiliationPlace>
   </Affiliation>
   <Affiliation Usage='BD'>
    <AffiliationName>National Cancer Institute of Canada Clinical Trials Group</AffiliationName>
    <AffiliationPlace>Kingston, Ontario, Canada</AffiliationPlace>
   </Affiliation>
   <Affiliation Usage='SR'>
    <AffiliationName>Ontario Institute for Cancer Research &amp; NCIC Clinical Trials Group</AffiliationName>
   </Affiliation>
  </Affiliations>""",
    'JAMES NEIFELD': """\
  <Affiliations>
   <Affiliation>
    <AffiliationName>Medical College of Virginia Hospital</AffiliationName>
    <AffiliationName>Virginia Commonwealth University</AffiliationName>
    <AffiliationPlace>Richmond, VA</AffiliationPlace>
   </Affiliation>
  </Affiliations>""",
    'R. RANEY': """\
  <Affiliations>
   <Affiliation>
    <AffiliationName>Dell Children's Medical Center of Central Texas</AffiliationName>
    <AffiliationPlace>Austin, TX</AffiliationPlace>
   </Affiliation>
  </Affiliations>""",
    'BARRY EAGEL': """\
  <Affiliations>
   <Affiliation>
    <AffiliationName>National Institutes of Health/SAIC</AffiliationName>
    <AffiliationPlace>Frederick, MD</AffiliationPlace>
   </Affiliation>
   <Affiliation>
    <AffiliationName>University of Connecticut</AffiliationName>
    <AffiliationPlace>Farmington, CT</AffiliationPlace>
   </Affiliation>
  </Affiliations>""",
    'JEAN FOURCROY': """\
  <Affiliations>
   <Affiliation>
    <AffiliationPlace>Frederick, MD</AffiliationPlace>
   </Affiliation>
  </Affiliations>""",
    'REBECCA SMITH-BINDMAN': """\
  <Affiliations>
   <Affiliation>
    <AffiliationName>University of California San Francisco</AffiliationName>
    <AffiliationName>Mount Zion Medical Center</AffiliationName>
    <AffiliationPlace>San Francisco, CA</AffiliationPlace>
   </Affiliation>
  </Affiliations>""" }

print "<PDQBoardMembers>"
for board in boards:
    url = 'http://www.cancer.gov/cancertopics/pdq/%s-board' % board
    #print url
    page = urllib.urlopen(url).read()
    for match in pattern.findall(page):
        name = match[0].split(',')[0]
        pieces = name.split()
        key = ("%s %s" % (pieces[0], pieces[-1])).upper()
        ids = members.get(key, ("UNKNOWN", "UNKNOWN"))
        affils = specials.get(key)
        lines = []
        for line in match[1].split('<br />'):
            stripped = line.strip()
            if stripped:
                lines.append(stripped)
        fp = len(lines) == 2 and standard or exceptions
        fp.write("%s (%s, %s, %s)\n" % (name, board, ids[0], ids[1]))
        print """\
 <PDQBoardMember person-id='%s' board-member-id='%s' source='%s'>
  <PDQBoardMemberName>%s</PDQBoardMemberName>
  <PDQBoard>%s</PDQBoard>""" % (ids[0], ids[1], url, name, boards[board])
        if affils:
            print affils
        elif len(lines) != 2:
            raise Exception(repr(lines))
        else:
            print """\
  <Affiliations>
   <Affiliation>
    <AffiliationName>%s</AffiliationName>
    <AffiliationPlace>%s</AffiliationPlace>
   </Affiliation>
  </Affiliations>""" % (lines[0], lines[1])
        for line in lines:
            if line:
                fp.write("\t%s\n" % line)
        print """\
 </PDQBoardMember>"""
print "</PDQBoardMembers>"
standard.close()
exceptions.close()
