#!/usr/bin/env python

"""Launch web browser to display a CDR XML document from the command line.
"""

import argparse
import urllib.request
import urllib.parse
import urllib.error
import webbrowser

try:
    from cdrapi.settings import Tier
    TIER = Tier().name
except Exception:
    TIER = "PROD"

TIERS = {
    "PROD": "cdr.cancer.gov",
    "STAGE": "cdr-stage.cancer.gov",
    "QA": "cdr-qa.cancer.gov",
    "DEV": "cdr-dev.cancer.gov"
}
VERSION_TYPES = "cwd", "latest", "lastpub", "exported", "num"

parser = argparse.ArgumentParser()
parser.add_argument("id", type=int)
parser.add_argument("--tier", "-t", choices=sorted(TIERS))
parser.add_argument("--host", "-s")
parser.add_argument("--version", "-v", type=int)
parser.add_argument("--named-version", "-n", choices=VERSION_TYPES)
args = parser.parse_args()
host = args.host or TIERS.get(args.tier or TIER)
if "." not in host:
    host += ".cancer.gov"
parms = {"doc-id": args.id}
if args.version:
    parms["version"] = args.version
    parms["vtype"] = "num"
elif args.named_version:
    parms["vtype"] = args.named_version
parms = urllib.parse.urlencode(parms)
url = "https://%s/cgi-bin/cdr/ShowCdrDocument.py?%s" % (host, parms)
webbrowser.open_new_tab(url)
