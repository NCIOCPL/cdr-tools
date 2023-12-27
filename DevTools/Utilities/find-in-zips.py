#!/usr/bin/env python3
# ----------------------------------------------------------------------
#
# Find substring in contents of zipfiles.
#
# ----------------------------------------------------------------------
from glob import glob
from re import compile, IGNORECASE
from sys import argv, stderr
from zipfile import ZipFile


def usage():
    stderr.write("usage: find-in-zips.py zip-pattern file-pattern target\n")
    stderr.write(" e.g.: find-in-zips.py *2005*.zip .*\\.xml wv008\\s*a\n")
    stderr.write("\n(note that the first argument is a file glob pattern\n")
    stderr.write("and the remaining args are regular expressions).\n")
    exit(2)


def searchZip(name, filePattern, targetPattern):
    try:
        z = ZipFile(name)
        for n in z.namelist():
            if filePattern.search(n):
                d = z.read(n)
                if targetPattern.search(d):
                    print(name, n)
    except Exception as e:
        print("%s: %s" % (name, e))


def main():
    if len(argv) != 4:
        usage()
    zipPattern, filePattern, target = argv[1:]
    filePattern = compile(filePattern, IGNORECASE)
    targetPattern = compile(target, IGNORECASE)
    for name in glob(zipPattern):
        searchZip(name, filePattern, targetPattern)


if __name__ == '__main__':
    main()
