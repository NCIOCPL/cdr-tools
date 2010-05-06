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

def submitQuery(params, which):
    start = time.time()
    url  = "http://clinicaltrials.gov/ct2/results"
    params.append('&studyxml=true')
    params = ''.join(params)
    print params
    urlobj = urllib.urlopen("%s?%s" % (url, params)) # GET request
    page = urlobj.read()
    name = 'd:/tmp/%s-ctgov-query.zip' % which
    fp = open(name, "wb")
    fp.write(page)
    fp.close()
    fp = open(name, 'rb')
    zf = zipfile.ZipFile(fp)
    s = set(zf.namelist())
    saveSet(s, 'd:/tmp/%s-ctgov-query.set' % which)
    print "elapsed: %f seconds" % (time.time() - start)
    return s

def saveSet(s, filename):
    fp = open(filename, 'w')
    names = list(s)
    names.sort()
    for n in names:
        fp.write("%s\n" % n)
    fp.close()

#----------------------------------------------------------------------
# This is how we currently ask for trials.
#----------------------------------------------------------------------
conditions = ('cancer', 'lymphedema', 'myelodysplastic syndromes',
              'neutropenia', 'aspergillosis', 'mucositis')
connector = ''
params = ["term="]
for condition in conditions:
    params.append(connector)
    params.append('(')
    params.append(condition.replace(' ', '+'))
    params.append(')+%5BCONDITION%5D')
    connector = '+OR+'
baseParams = list(params)
oldList = submitQuery(params, "old")
print "%d files in result from original query" % len(oldList)

#----------------------------------------------------------------------
# William and Lakshmi have asked that we add this approach.
#----------------------------------------------------------------------
params = ["term=(cancer+OR+neoplasm)+%5BDISEASE%5D"]
newList = submitQuery(params, "new")
print "%d files in result from new query" % len(newList)

#----------------------------------------------------------------------
# Compare the two results sets.
#----------------------------------------------------------------------
oldNotNew = oldList.difference(newList)
print "%d files in old set but not in new" % len(oldNotNew)
saveSet(oldNotNew, 'd:/tmp/old-not-new.set')
newNotOld = newList.difference(oldList)
print "%d files in new set but not in old" % len(newNotOld)

#----------------------------------------------------------------------
# Merge the two sets together.
#----------------------------------------------------------------------
saveSet(newNotOld, 'd:/tmp/new-not-old.set')
combo = oldList.union(newList)
print "%d files in combined set" % len(combo)
saveSet(combo, 'd:/tmp/combined.set')

#----------------------------------------------------------------------
# See if a single query can be used to get the same combined results.
#----------------------------------------------------------------------
params = ['term=(cancer+OR+neoplasm)+[DISEASE]',
          '+OR+',
          '(lymphedema+OR+myelodysplastic+syndromes+OR+',
          'neutropenia+OR+aspergillosis+OR+mucositis)+[CONDITION]']
comboList = submitQuery(params, "combo")
print "%d files in result from combo query" % len(comboList)
saveSet(comboList, 'd:/tmp/direct-combo.set')
print ("two approaches to fetching combined lists %s" %
       combo == comboList and "match" or "differ")
