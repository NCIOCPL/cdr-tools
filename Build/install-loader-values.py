#!/usr/bin/env python

"""Populate the CDR `ctl` table from files pulled from a git repo branch.

These are values used by ElasticSearch index loaders. The values will be
in files contained in a single directory (typically Database/Loader from
a branch of the cdr-server GitHub repository).
"""

from argparse import ArgumentParser
from json import load, dumps
from pathlib import Path
from cdrapi import db
from cdr import getpw, login, updateCtl, Logging

ACCOUNT = "ReleaseInstaller"
EXTENSIONS = "json", "txt"

logger = Logging.get_logger("deploy", console=True)
parser = ArgumentParser()
parser.add_argument("--directory", "-d", required=True)
parser.add_argument("--tier", "-t")
parser.add_argument("--session", "-s")
parser.add_argument("--group", "-g")
parser.add_argument("--name", "-n")
parser.add_argument("--verbose", "-v", action="store_true")
opts = parser.parse_args()
logger.info("installing from %s", opts.directory)
try:
    if opts.session:
        session = opts.session
    else:
        password = getpw(ACCOUNT)
        session = login(ACCOUNT, password)
    cursor = db.connect(user="CdrGuest", tier=opts.tier).cursor()
    directory = Path(opts.directory)
    update_opts = dict(tier=opts.tier)
    for path in directory.iterdir():
        if path.is_file():
            name = path.name
            parts = name.split(".")
            if len(parts) == 2:
                name, ext = parts
                if ext in EXTENSIONS:
                    parts = name.split("--")
                    if len(parts) == 2:
                        group, name = parts
                        if not opts.name or opts.name == name:
                            if not opts.group or opts.group == group:
                                logger.info("group=%s name=%s", group, name)
                                value = path.read_text("utf-8")
                                query = db.Query("ctl", "comment")
                                query.where(query.Condition("grp", group))
                                query.where(query.Condition("name", name))
                                query.where("inactivated IS NULL")
                                rows = query.execute(cursor).fetchall()
                                comment = rows[0].comment if rows else None
                                if opts.verbose:
                                    print(f"{group}:{name}={comment}")
                                update_opts["group"] = group
                                update_opts["name"] = name
                                update_opts["value"] = value
                                update_opts["comment"] = comment
                                updateCtl(session, "Create", **update_opts)
except Exception as e:
    logger.exception("installing loader values")
