#!/usr/bin/env python3

"""Test connection to SQL Server.

Defaults to the SQL Server 2019 server on the DEV tier. Can be switched
to another server with the `--server` option.
"""

from argparse import ArgumentParser
from pyodbc import connect
from cdrapi import settings

DRIVER = "{ODBC Driver 17 for SQL Server}"
SERVER = "NCIDB-D412-V\MSSQLOCPLBLUE,52300"
TIER = settings.Tier()
ACCOUNTS = "CdrSqlAccount", "CdrPublishing", "CdrGuest"
DATABASES = "CDR", "cdr_archived_versions"


def go(label, **opts):
    try:
        cstring = "".join(f"{name}={value};" for name, value in opts.items())
        conn = connect(cstring)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM INFORMATION_SCHEMA.TABLES")
        rows = cursor.fetchall()
        print(f"{label}: {len(rows)} tables visible")
    except Exception as e:
        print(f"{label}: {e}")


parser = ArgumentParser()
parser.add_argument("--server", default=SERVER)
opts = parser.parse_args()
for db in DATABASES:
    dbopts = dict(driver=DRIVER, server=opts.server, database=db)
    connection_opts = dict(dbopts)
    connection_opts["Trusted_Connection"] = "yes"
    go(f"{db} (trusted)", **connection_opts)
    for account in ACCOUNTS:
        connection_opts = dict(dbopts)
        connection_opts["Uid"] = account
        connection_opts["Pwd"] = TIER.password(account, "CDR")
        go(f"{db} ({account})", **connection_opts)
