#!/usr/bin/env python
# ----------------------------------------------------------------------
# Tool for generating script to drive get-prod-scripts.py.
#
# Example usage:
#  1. mkdir prod-20150106
#  2. cd prod-20150106
#  3. set SESS="--session CDR-SESSION-ID"
#  3. python ../create-script-for-prod-scripts.py %SESS% > get-prod-files.cmd
#  4. get-prod-files.cmd
#
# To fetch from a non-prod tier, add --tier TIER (e.g. --tier stage)
# ----------------------------------------------------------------------
import argparse
import logging
import re
import requests

parser = argparse.ArgumentParser()
parser.add_argument("--session", required=True)
parser.add_argument("--tier")
opts = parser.parse_args()
tier = opts.tier and ("-%s" % opts.tier.lower()) or ""
BASE = "https://cdr%s.cancer.gov/cgi-bin/cdr/log-tail.py" % tier
DIRS = ("cdr/Bin", "cdr/ClientFiles", "cdr/Database", "cdr/etc", "cdr/Lib",
        "cdr/Licensee", "cdr/Mailers", "cdr/Publishing", "cdr/Utilities",
        "etc", "Inetpub/wwwroot", "cdr/glossifier", "cdr/Scheduler",
        "cdr/Build")

logging.basicConfig(
    format="%(asctime)s %(message)s",
    filename="create-script-for-prod-files.log",
    level=logging.INFO
)


def unwanted(path):
    p = path.lower()
    if p.endswith(r"\cvs"):
        return True
    prefixes = (
        r"d:\cdr\mailers\output",
        r"d:\cdr\utilities\ctgovdownloads",
        r"d:\cdr\utilities\bin\ctrpdownloads",
        r"d:\etc\boundschecker",
        r"d:\etc\emacs",
        r"d:\etc\lisp",
        r"d:\etc\localtexmf",
        r"d:\etc\vim",
    )
    for prefix in prefixes:
        if p.startswith(prefix):
            return True
    return False


def make_command(path, opts):
    command = ["python ../get-prod-scripts.py --session %s" % opts.session]
    if opts.tier:
        command.append("--tier %s" % opts.tier)
    command.append('--path "%s"' % path)
    command.append('--dir "%s"' % path[3:])
    return " ".join(command)


base = "%s?Session=%s" % (BASE, opts.session)
logging.info("base=%s", base)
for d in DIRS:
    path = d.replace("/", "\\")
    url = "%s&Request=Submit&p=d:\\%s\\*/s/ad" % (base, path)
    logging.info(url)
    response = requests.get(url)
    with open("responses.txt", "a") as fp:
        fp.write(response.text)
        fp.write("\n****************************************\n")
    for line in response.text.splitlines():
        match = re.search("Directory of (d:.+)", line.strip())
        if match:
            path = match.group(1)
            if not unwanted(path):
                print((make_command(path, opts)))
