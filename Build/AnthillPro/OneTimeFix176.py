# One time change to publishing control doc 176.xml
#
# Converts output directory
#  from: d:\cdr\mailers\output
#    to: d:\cdr\Output\mailers

import cdr

session = cdr.login('ahm', 'cdrAhm')

old176xml = cdr.getDoc(session, 176, checkout='Y', getObject=False)

tmp176xml = old176xml.replace('d:/cdr/mailers/output/',
                              'd:/cdr/Output/Mailers/', 99);

# Fix an insignificant inconsistency in the data
new176xml = tmp176xml.replace('d:/cdr/mailers/output',
                              'd:/cdr/Output/Mailers/', 99);

print("type old doc=%s" % type(old176xml))
print("type new doc=%s" % type(new176xml))

fp = open('test176.xml', 'w')
fp.write(new176xml)
fp.close

# Replace in the database
cmt = "Moving all outputs from cdr/mailers/output to cdr/Output/mailers"
result = cdr.repDoc(session, doc=new176xml, checkIn='Y', val='Y', ver='Y',
                    comment=cmt, reason=cmt, showWarnings=True)

print result
