#----------------------------------------------------------------------
#
# $Id$
#
# [CTGOV] Automate export jobs - Part II (Compare Data)
#
# "Mark Leech provided us with a document identifying all protocols the NLM
# currently has from the CDR.  We want to compare NLM's list with the picture
# that we think the NLM should have."
#
# BZIssue::3617
#
#----------------------------------------------------------------------
import re, cdr

def cdrIntId(cdrId):
    return cdr.exNormalize(cdrId)[1]

notAtNlm = {}
notInRecords = {}
duplicate = {}
dropped = {}
mismatch = {}
fp = open('attachment.cgi@id=1331')
for line in fp.readlines():
    line = line.strip()
    match = re.search("last sent (CDR\\d+) to NLM on (.+) but", line)
    if match:
        notAtNlm[cdrIntId(match.group(1))] = match.group(2)
        continue
    match = re.search("says they created (NCT\\d+) from (.+), but that's", line)
    if match:
        nctId, cdrId = match.groups()
        if cdrId.startswith('199'):
            continue
        if cdrId.startswith('2007C'):
            continue
        if cdrId.startswith('CDR'):
            notInRecords[cdrIntId(cdrId)] = nctId
            continue
    match = re.search("sent '(.+)' as the status for (CDR\\d+) \((NCT\\d+)\) "
                      "but NLM has '(.+)'", line)
    if match:
        cdrId = cdrIntId(match.group(2))
        mismatch[cdrId] = (match.group(3), match.group(1), match.group(4))
        continue
    match = re.search("that (CDR\\d+) \((NCT\\d+)\) had been dropped on (.+) "
                      "but they still have it with status (.+)", line)
    if match:
        cdrId = cdrIntId(match.group(1))
        dropped[cdrId] = (match.group(2), match.group(3), match.group(4))
        continue
    match = re.search("DUPLICATE ROWS FOR (NCT\\d+): (CDR\\d+) AND (CDR\\d+)",
                      line)
    if match:
        duplicate[match.group(1)] = (cdrIntId(match.group(2)),
                                     cdrIntId(match.group(3)))
        continue
    raise Exception("unmatched line %s" % line)
html = ["""\
<html>
 <head>
  <title>CT.gov/CDR Discrepancies</title>
  <style type='text/css'>
   body { font-family: Arial; font-size: 10pt }
   h1   { font-size: 14pt; }
   h2   { font-size: 12pt; }
  </style>
 </head>
 <body>
  <h1>CT.gov/CDR Discrepancies</title>
  <h2>Duplicate NCT IDs</h2>
  <table border='1' cellpadding='2' cellspacing='0'>
   <tr>
    <th>NCT ID</th>
    <th colspan='2'>CDR IDs</th>
   </tr>
"""]
keys = duplicate.keys()
keys.sort()
for key in keys:
    html.append("""\
   <tr>
    <td>%s</td>
    <td>%d</td>
    <td>%d</td>
   </tr>
""" % (key, duplicate[key][0], duplicate[key][1]))
html.append("""\
  </table>
  <br />
  <h2>Trials Dropped From CDR Which Are Still in CT.gov</h2>
  <table border='1' cellpadding='2' cellspacing='0'>
   <tr>
    <th>CDR ID</th>
    <th>NCT ID</th>
    <th>Dropped</th>
    <th>Status</th>
   </tr>
""")
keys = dropped.keys()
keys.sort()
for key in keys:
    trial = dropped[key]
    html.append("""\
   <tr>
    <td>%d</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
   </tr>
""" % (key, trial[0], trial[1], trial[2]))
html.append("""\
  </table>
  <br />
  <h2>Status Mismatches</h2>
  <table border='1' cellpadding='2' cellspacing='0'>
   <tr>
    <th>CDR ID</th>
    <th>NCT ID</th>
    <th>Sent Status</th>
    <th>CT.gov Status</th>
   </tr>
""")
keys = mismatch.keys()
keys.sort()
for key in keys:
    trial = mismatch[key]
    html.append("""\
   <tr>
    <td>%d</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
   </tr>
""" % (key, trial[0], trial[1], trial[2]))
html.append("""\
  </table>
  <br />
  <h2>Trials in CT.gov But Not In Our Export Records</h2>
  <table border='1' cellpadding='2' cellspacing='0'>
   <tr>
    <th>CDR ID</th>
    <th>NCT ID</th>
   </tr>
""")
keys = notInRecords.keys()
keys.sort()
for key in keys:
    html.append("""\
   <tr>
    <td>%d</td>
    <td>%s</td>
   </tr>
""" % (key, notInRecords[key]))
html.append("""\
  </table>
  <br />
  <h2>Trials Sent To CT.gov But Not In Their Report</h2>
  <table border='1' cellpadding='2' cellspacing='0'>
   <tr>
    <th>CDR ID</th>
    <th>Last Sent</th>
   </tr>
""")
keys = notAtNlm.keys()
keys.sort()
for key in keys:
    html.append("""\
   <tr>
    <td>%d</td>
    <td>%s</td>
   </tr>
""" % (key, notAtNlm[key]))
html.append("""\
  </table>
 </body>
</html>
""")
html = "".join(html)
fp = open("ReportForIssue3617.html", "w")
fp.write(html)
fp.close()
