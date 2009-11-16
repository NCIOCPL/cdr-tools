#----------------------------------------------------------------------
#
# $Id$
#
# Script to fetch a single XML ClinicalTrials.gov document from NLM given
# the trial's NCT ID.
#
#----------------------------------------------------------------------
import zipfile, sys, urllib, time

def usage():
    sys.stderr.write("usage: GetCTGovProtocol.py NCT-ID\n")
    sys.exit(2)
def main():
    if len(sys.argv) != 2:
        usage()
    else:
        nctId = sys.argv[1]
        now = time.strftime("%Y%m%d%H%M%S")
        zipName = time.strftime("d:/tmp/%s-%s.zip" % (nctId, now))
        url  = "http://clinicaltrials.gov/ct2/results"
        params = "term=%s&studyxml=true" % nctId
        try:
            urlobj = urllib.urlopen("%s?%s" % (url, params))
            page = urlobj.read()
        except Exception, e:
            sys.stderr.write("Failure downloading %s: %s\n" % (nctId, e))
            sys.exit(1)
        try:
            fp = open(zipName, "wb")
            fp.write(page)
            fp.close()
            print "downloaded %s" % zipName
        except Exception, e:
            sys.stderr.write("Failure writing %s: %s\n" % (zipName, e))
            sys.exit(3)
        try:
            n = "%s.xml" % nctId
            fp = open(zipName, "rb")
            z = zipfile.ZipFile(fp)
            x = z.read(n)
        except Exception, e:
            sys.stderr.write("Unable to extract %s from %s: %s\n" %
                             (n, zipName, e))
            sys.exit(4)
        print x

if __name__ == '__main__':
    main()
