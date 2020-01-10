#!/usr/bin/env python

"""Demonstrate how to call a stored procedure.

Illustrates invocation of a stored procedure to obtain the last results
set when the number of results sets is unknown.  Assumes that no interim
results sets (nor the final results set, for that matter) will be so
prohibitively large that keeping the entire set in memory is an unacceptable
option.

New example program for Alan.

Modified 2019-09-15 for pyodbc, which doesn't have a callproc method.
See https://github.com/mkleehammer/pyodbc/wiki/Calling-Stored-Procedures
Also upgraded to Python 3.
"""

from argparse import ArgumentParser
import datetime
from cdrapi import db

def get_last_results_set(cursor, proc_name, params):
    cursor.execute(f"{{CALL {proc_name} (?)}}", params)
    # cursor.execute(f"EXEC {proc_name} ?", params) also works
    lastSet = []
    done = False
    while not done:
        if cursor.description:
            lastSet = cursor.fetchall()
        if not cursor.nextset():
            done = True
    return lastSet

cursor = db.connect().cursor()
parser = ArgumentParser()
default = datetime.datetime.today() - datetime.timedelta(2)
parser.add_argument("--param", default=default)
opts = parser.parse_args()
param = opts.param
print(get_last_results_set(cursor, "cdr_changed_docs", (param,)))
