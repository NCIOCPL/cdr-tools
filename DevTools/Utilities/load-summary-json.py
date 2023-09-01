#!/usr/bin/env python

"""Push PDQ summaries to Drupal.

This script decouples the push portion of CDR publishing so that it can
be performed from outside the NIH firewall/network, avoiding any problems
that might be introduced by that layer.

The required --directory option give the path to the top-level directory
in which the output from the companion script get-summary-json.py has
stored the JSON files for the summaries to be loaded.

The required --target option provides the base URL for the Drupal server.

The required --password option is used to specify the password for the
Drupal PDQ account.

The optional --cis or --dis flag options can restrict the load to either
cancer information summaries or drug information summaries. By default,
both sets are loaded.

We provide all of the values (auth, logger, batch_size) for which the Drupal
client class would need to use a Session object, so that we can pass None
as the session argument to the DrupalClient constructor. We do this because
the Session constructor needs to connect to the CDR database, which will not
be accessible from outside the NIH firewall (and not even accessible from some
developer workstations inside that firewall).

Pushing only CIS to a Drupal instance in a local Docker container takes about
nine minutes, with the total job taking 13.5 minutes. Pushing to an Acquia ODE
takes about 17.5 minutes, with the total job taking a little under 25 minutes.
"""

from argparse import ArgumentParser
from datetime import datetime
from json import load
from pathlib import Path
from sys import stderr
from cdr import Logging
from cdrapi.publishing import DrupalClient


# Collect the settings controlled by the command-line options.
parser = ArgumentParser()
parser.add_argument("--directory", "-d", required=True)
parser.add_argument("--target", "-t", required=True)
parser.add_argument("--password", "-p", required=True)
group = parser.add_mutually_exclusive_group()
group.add_argument("--cis", action="store_true", help="CIS only")
group.add_argument("--dis", action="store_true", help="DIS only")
opts = parser.parse_args()
auth = "PDQ", opts.password
logger = Logging.get_logger("load-summary-json")
if opts.dis:
    directories = [Path(opts.directory) / "DrugInformationSummary"]
elif opts.cis:
    directories = [
        Path(opts.directory) / "Summary/English",
        Path(opts.directory) / "Summary/Spanish",
    ]
else:
    directories = [
        Path(opts.directory) / "Summary/English",
        Path(opts.directory) / "Summary/Spanish",
        Path(opts.directory) / "DrugInformationSummary",
    ]

# Push the summaries to the Drupal server.
opts = dict(auth=auth, base=opts.target, logger=logger, batch_size=25)
client = DrupalClient(None, **opts)
pushed = []
start = datetime.now()
for directory in directories:
    for path in directory.glob("*.json"):
        with path.open(encoding="utf-8") as fp:
            values = load(fp)
        nid = client.push(values)
        langcode = values.get("language", "en")
        cdr_id = values["cdr_id"]
        pushed.append((cdr_id, nid, langcode))
        elapsed = datetime.now() - start
        stderr.write(f"\rpushed {len(pushed)} summaries in {elapsed}  ")
stderr.write("\n")

# Move the summaries from draft mode to published.
errors = client.publish(pushed)
stderr.write(f"publish complete\n")
if errors:
    stderr.write(f"{len(errors)} Drupal publish errors; see logs\n")

# Let the user know how long the push/publish job took.
elapsed = datetime.now() - start
stderr.write(f"job complete in {elapsed}\n")
