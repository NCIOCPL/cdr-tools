#!/usr/bin/env python3

"""Get the JSON serialization of a PDQ node's values.

In the case of a Cancer Information Summary node, the values can represent
both an English and a Spanish CDR summary document.

The JSON serialization is written to stdout, and can be piped to
./yaml-from-json.py to produce sample node values for regression testing.

By default node values are fetched from the production server. Use the --base
option to override this behavior, supplying the base URL for the site without
a trailing slash. If you are on a machine over which you are confident you
have complete control (usually a risky assumption), you can put the password
for the PDQ account on the server you will use in a file in the current
working directory under the name "pdqpw" (not generally recommended). You
can also supply the password as a command-line option, but that too has its
security risks. Safest is to let the script prompt for the password.

You can supply an optional integer for the --indent argument on the command
line to have the output pretty-printed.

You must supply an integer for the Drupal node's ID (--node) and either "cis"
or "dis" for the --type argument indicating whether the node's content type
is pdq_cancer_information_summary or pdq_drug_information_summary.
"""

from argparse import ArgumentParser
from getpass import getpass
from json import loads, dumps
from requests import get

BASE = "https://www-cms.cancer.gov"
TYPES = "cis", "dis"

parser = ArgumentParser()
parser.add_argument("--base", "-b", default=BASE)
parser.add_argument("--node", "-n", required=True, type=int)
parser.add_argument("--type", "-t", required=True, choices=TYPES)
parser.add_argument("--password", "-p")
parser.add_argument("--indent", "-i", type=int, default=0)
opts = parser.parse_args()
password = opts.password
if not password:
    try:
        with open("pdqpw") as fp:
            password = fp.read().strip()
    except Exception:
        pass
if not password:
    password = getpass("password for PDQ account: ")
if not password:
    raise Exception("No credentials")
auth = "PDQ", password
url = f"{opts.base}/pdq/api/{opts.type}/{opts.node}"
response = get(url, auth=auth)
if not response.ok:
    raise Exception(response.reason)
if opts.indent:
    print(dumps(loads(response.text), indent=opts.indent))
else:
    print(response.text, end="")
