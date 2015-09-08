import datetime
import os
import sys

start = len(sys.argv) > 1 and sys.argv[1] or "."
files = []
for base, dirs, names in os.walk(start):
    for name in names:
        path = ("%s/%s" % (base, name)).replace("\\", "/")
        stat = os.stat(path)
        mtime = datetime.datetime.fromtimestamp(stat.st_mtime)
        stamp = mtime.strftime("%Y-%m-%d %H:%M:%S.%f")
        files.append((stamp, path))
for stamp, path in sorted(files):
    print stamp, path
