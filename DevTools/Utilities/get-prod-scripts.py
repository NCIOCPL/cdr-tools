#!/usr/bin/env python
#----------------------------------------------------------------------
# Tool for pulling scripts from a production directory down to the
# local file system.  Doesn't recurse.  Handles binary files.
#----------------------------------------------------------------------
import argparse
import os
import re
import sys
import requests

parser = argparse.ArgumentParser()
parser.add_argument("--session", required=True)
parser.add_argument("--tier")
parser.add_argument("--path", default=r"d:\Inetpub\wwwroot\cgi-bin\cdr")
parser.add_argument("--dir", default="cgi-prod")
opts = parser.parse_args()
tier = opts.tier and ("-%s" % opts.tier.lower()) or ""
args = (tier, "Request=Submit", opts.session)
BASE = "https://cdr%s.cancer.gov/cgi-bin/cdr/log-tail.py?%s&Session=%s" % args

try:
    os.makedirs(opts.dir)
    sys.stderr.write("created %s\n" % opts.dir)
except:
    sys.stderr.write("%s already created\n" % opts.dir)

response = requests.get("%s&p=%s\\*" % (BASE, opts.path))
names = []
for line in response.text.splitlines():
    pieces = re.split("\\s+", line.strip(), 4)
    if len(pieces) == 5 and pieces[2] in ("AM", "PM") and pieces[3] != "<DIR>":
        names.append(pieces[4])
done = 0
for name in sorted(names):
    path = "%s\\%s" % (opts.path, name.replace(" ", "+"))
    try:
        response = requests.get("%s&r=1&p=%s" % (BASE, path))
        script = response.content
        with open("%s/%s" % (opts.dir, name), "wb") as fp:
            fp.write(script)
    except Exception as e:
        with open("get-prod-scripts.err", "a") as fp:
            fp.write("%s: %s\n" % (path, e))
        sys.stderr.write("\n%s: %s\n" % (path, e))
    done += 1
    sys.stderr.write("\rretrieved %d of %d" % (done, len(names)))
sys.stderr.write("\n")
