#----------------------------------------------------------------------
#
# $Id$
#
# Retrieve sets of trials from CTRP and queue them form import.
#
# See https://trials.nci.nih.gov/pa/pdqgetAvailableFiles.action
# for list of trial sets currently available for retrieval.
#----------------------------------------------------------------------
import lxml.etree as etree, sys, urllib2, zipfile, cdr, os

RSS = "CTEPRSS RSS"
BASE = "https://trials.nci.nih.gov/pa/pdqgetFileByDate.action"
BASE = "https://trials-qa.nci.nih.gov/pa/pdqgetFileByDate.action"
LOGFILE = cdr.DEFAULT_LOGDIR + "/DownloadCtrpTrials.log"

class Trial:
    def __init__(self, archive, docName):
        self.name = docName
        self.owners = set()
        try:
            xmlDoc = archive.read(docName)
        except Exception, e:
            message = "Failure reading %s: %s" % (docName, repr(e))
            raise Exception(message)
        try:
            self.tree = etree.fromstring(xmlDoc)
        except Exception, e:
            message = "Failure parsing %s: %s" % (docName, repr(e))
            raise Exception(message)
        if self.tree.tag != 'clinical_study':
            message = "%s is not a clinical study" % docName
            raise Exception(message)
        for owner in self.tree.findall('trial_owners/name'):
            self.owners.add(owner.text)

class TrialSet:
    def __init__(self, date):
        self.date = date
        self.trials = []
        self.inScope = 0
        url = "%s?date=CTRP-TRIALS-%s.zip" % (BASE, date)
        try:
            server = urllib2.urlopen(url)
            doc = server.read()
        except Exception, e:
            message = "Failure retrieving %s: %s" % (url, repr(e))
            cdr.logwrite(message, LOGFILE)
            raise cdr.Exception(message)
        try:
            path = "CTRP-TRIALS-%s.zip" % date
            fp = open(path, "wb")
            fp.write(doc)
            fp.close()
        except Exception, e:
            message = "Failure storing %s: %s" % (path, repr(e))
            cdr.logwrite(message, LOGFILE)
            raise cdr.Exception(message)
        try:
            fp = open(path, "rb")
            archive = zipfile.ZipFile(fp)
            nameList = archive.namelist()
        except Exception, e:
            message = "Failure opening %s: %s" % (path, repr(e))
            cdr.logwrite(message, LOGFILE)
            raise cdr.Exception(message)
        for docName in nameList:
            if docName.lower().endswith(".xml"):
                try:
                    trial = Trial(archive, docName)
                    self.trials.append(trial)
                    if RSS in trial.owners:
                        self.inScope += 1
                except Exception, e:
                    cdr.logwrite(str(e), LOGFILE)

def init():
    curdir = os.getcwd()
    downloadDirectory = os.path.join(curdir, "CTRPDownloads")
    os.makedirs(downloadDirectory)
    os.chdir(downloadDirectory)
    cdr.logwrite("current directory is '%s'\n" % downloadDirectory, LOGFILE)

def main():
    init()
    if len(sys.argv) > 1:
        trialSet = TrialSet(sys.argv[1])
        print "downloaded %d trials (%s in scope)" % (len(trialSet.trials),
                                                      trialSet.inScope)

main()
