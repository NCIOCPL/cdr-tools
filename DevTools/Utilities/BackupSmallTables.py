#!/usr/bin/env python3

"""Back up the configuration CDR tables over HTTP.
"""

from argparse import ArgumentParser
from datetime import datetime
from os import mkdir
from requests import get

URL = "https://{}.cancer.gov/cgi-bin/cdr/CdrQueries.py?Request=JSON"
URL += "&sql=SELECT+*+FROM+{}"
TABLES = (
    "action",
    "active_status",
    "ctl",
    "doc_status",
    "doc_type",
    "format",
    "glossary_translation_state",
    "grp",
    "grp_action",
    "grp_usr",
    "link_prop_type",
    "link_properties",
    "link_target",
    "link_type",
    "link_xml",
    "media_translation_state",
    "query_term_def",
    "query_term_rule",
    "scheduled_job",
    "summary_change_type",
    "summary_translation_state",
    "usr",
)
TIERS = dict(
    PROD="cdr",
    STAGE="cdr-stage",
    QA="cdr-qa",
    DEV="cdr-dev",
)
CHOICES = TIERS.keys()

parser = ArgumentParser()
parser.add_argument("--tier", choices=CHOICES, default="PROD")
opts = parser.parse_args()
now = datetime.now()
stamp = now.strftime("%Y%m%d%H%M")
directory = f"cdr-small-table-backup-{opts.tier.lower()}-{stamp}"
mkdir(directory)
for table in TABLES:
    url = URL.format(TIERS[opts.tier], table)
    response = get(url)
    with open(f"{directory}/{table}.json", "w", encoding="utf-8") as fp:
        fp.write(response.text.replace("\r", ""))
elapsed = datetime.now() - now
print(f"backup in {directory} (elapsed {elapsed})")
