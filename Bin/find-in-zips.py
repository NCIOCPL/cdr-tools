#----------------------------------------------------------------------
#
# $Id$
#
# Find substring in contents of zipfiles.
#
#----------------------------------------------------------------------
import zipfile, glob, sys, re

def usage():
    sys.stderr.write("usage: find-in-zips.py zip-pattern file-pattern target\n")
    sys.stderr.write(" e.g.: find-in-zips.py *2005*.zip .*\\.xml wv008\\s*a\n")
    sys.stderr.write("\n(note that the first argument is a file glob pattern\n")
    sys.stderr.write("and the remaining args are regular expressions).\n")
    sys.exit(2)

def searchZip(name, filePattern, targetPattern):
    try:
        z = zipfile.ZipFile(name)
        for n in z.namelist():
            if filePattern.search(n):
                d = z.read(n)
                if targetPattern.search(d):
                    print name, n
    except Exception, e:
        print "%s: %s" % (name, e)

def main():
    if len(sys.argv) != 4:
        usage()
    zipPattern, filePattern, target = sys.argv[1:]
    filePattern = re.compile(filePattern, re.I)
    targetPattern = re.compile(target, re.I)
    for name in glob.glob(zipPattern):
        searchZip(name, filePattern, targetPattern)

if __name__ == '__main__':
    main()
