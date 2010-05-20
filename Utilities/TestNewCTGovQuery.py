#----------------------------------------------------------------------
#
# $Id$
#
# "In the CDR status meeting today, we discussed the need to explore
# (on Mahler) modifications to the ctgov import program to retrieve
# trials that have 'cancer' and 'neoplasm' as part of their keywords."
#
# BZIssue::4817
#
#----------------------------------------------------------------------
import zipfile, sys, urllib, time

def submitQuery(paramsets, which):
    start = time.time()
    params = "term=" + (" OR ".join(paramsets)).replace(" ", "+") + "&studyxml=true"
    print params
    url  = "http://clinicaltrials.gov/ct2/results"
    urlobj = urllib.urlopen("%s?%s" % (url, params))
    page = urlobj.read()
    name = 'd:/tmp/%s-ctgov-query.zip' % which
    fp = open(name, "wb")
    fp.write(page)
    fp.close()
    fp = open(name, 'rb')
    zf = zipfile.ZipFile(fp)
    s = set(zf.namelist())
    saveSet(s, 'd:/tmp/%s-ctgov-query.set' % which)
    print "%s (%d hits): %f seconds" % (which, len(s), time.time() - start)
    return s

def saveSet(s, filename):
    fp = open(filename, 'w')
    names = list(s)
    names.sort()
    for n in names:
        fp.write("%s\n" % n)
    fp.close()

#----------------------------------------------------------------------
# Determine the difference between two query results sets.
#----------------------------------------------------------------------
def compareSets(oldSet, newSet, label):
    diffSet = newSet.difference(oldSet)
    print "%d in %s" % (len(diffSet), label)
    saveSet(diffSet, 'd:/tmp/%s.set' % label)

#----------------------------------------------------------------------
# Try several flavors of the query.
#----------------------------------------------------------------------
condition = ("(lymphedema OR myelodysplastic syndromes OR neutropenia OR "
             "aspergillosis OR mucositis OR cancer) [CONDITION]")
disease = "(cancer OR neoplasm) [DISEASE]"
sponsor = "(National Cancer Institute) [SPONSOR]"
list0 = submitQuery((condition,), "condition")
list1 = submitQuery((condition, disease), "condition+disease")
list2 = submitQuery((condition, disease, sponsor), "condition+disease+sponsor")
list3 = submitQuery((condition, sponsor), "condition+sponsor")

#----------------------------------------------------------------------
# Note the effect of adding NCI [sponsor].
#----------------------------------------------------------------------
compareSets(list0, list3, "sponsor-not-condition")
compareSets(list1, list2, "sponsor-not-condition-or-disease")
compareSets(list3, list2, "disease-not-condition-or-sponsor")
