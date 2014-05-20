#----------------------------------------------------------------------
#
# $Id$
#
# "Please remove the following NCT IDs from the duplicates file so that
# we can force download the trials: ...."
#
#----------------------------------------------------------------------
doomed = (
    'NCT00001506',
    'NCT00001575',
    'NCT00001238',
    'NCT00001813',
    'NCT00001163',
    'NCT00001823',
    'NCT00026689',
    'NCT00013533',
    'NCT00033137',
    'NCT00035373',
    'NCT00034424',
    'NCT00001186',
    'NCT00039676',
    'NCT00040352',
    'NCT00046189',
    'NCT00050752',
    'NCT00027274'
)
def skip(line):
    for nct_id in doomed:
        if nct_id in line:
            return True
    return False

fp = open("ctgov-dups.txt", "rb")
out = open("ctgov-dups-ocecdr-3767.txt", "wb")
for line in fp:
    #line = line.strip()
    if not skip(line):
        #out.write("%s\n" % line)
        out.write(line)
out.close()
fp.close()
