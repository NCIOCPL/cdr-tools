#!/usr/bin/env python3
# ********************************************************************
# File name: partner-data.py
#            --------------
# Test harness to access PDQ content partner information from the CDR
# ********************************************************************
import argparse
import urllib.request

HOST = "cdr-dev.cancer.gov"
URLS = dict(
    partners="get-pdq-partners.py",
    contacts="get-pdq-contacts.py",
    accesses="last-pdq-data-partner-accesses.py",
)

parser = argparse.ArgumentParser()
parser.add_argument("--host", default=HOST)
parser.add_argument("--url", default="partners", choices=list(URLS))
opts = parser.parse_args()
url = f"https://{opts.host}/cgi-bin/cdr/{URLS[opts.url]}"
print(url)
with urllib.request.urlopen(url) as response:
    print(response.read().decode("utf-8"))
