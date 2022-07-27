#!/usr/bin/env python

"""
Create a backup of a Python installation on a CDR server.

This is done in preparation for an upgrade of Python, which will replace
the existing Python directory.

Takes two command-line arguments, the first giving the drive letter for the
volume on which Python is installed, and the second giving the version number
being backed up. It is assumed that the name of the directory in which Python
is installed is "Python." The script also assumes there is a /tmp directory
on the drive where Python is installed.

For example:
    backup-python.py D 2.7.10

2021-12-31: this tool may no longer be needed, as the Python 3 installer
from python.org is able to upgrade in place.
"""

import datetime
import os
import subprocess
import sys


def report(what):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(("{} {}".format(now, what)))


if len(sys.argv) != 3:
    sys.stderr.write("usage: backup-python.py DRIVE VERSION\n")
    sys.stderr.write(" e.g.: backup-python.py D 2.7.10\n")
    sys.exit(1)
drive = sys.argv[1][0]
version = sys.argv[2]
os.chdir(drive + ":/")
if not os.path.isdir("Python"):
    report("nothing to back up")
else:
    now = datetime.datetime.now()
    stamp = now.strftime("%Y%m%d%H%M%S")
    path = "tmp/Python-{}-{}.tgz".format(version, stamp)
    args = "tar.exe", "-czf", path, "Python"
    stream = subprocess.Popen(args, shell=True,
                              stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT)
    output, error = stream.communicate()
    if stream.returncode:
        report("backup failure: {}".format(output))
        sys.exit(1)
    report("Python backed up to {}".format(path))
sys.exit(0)
