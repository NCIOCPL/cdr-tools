"""Print the scheduled CDR job settings to standard out.

Use the --json option to generate output usable by load-scheduled-jobs.py.
"""

from argparse import ArgumentParser
from json import dumps
from cdrapi import db

parser = ArgumentParser()
parser.add_argument("--tier")
parser.add_argument("--json", action="store_true")
opts = parser.parse_args()
cursor = db.connect(tier=opts.tier).cursor()
rows = cursor.execute("SELECT * FROM scheduled_job ORDER BY name")
if opts.json:
    print(dumps([tuple(row[1:]) for row in rows], indent=2))
else:
    for row in rows:
        print("-" * 70)
        print(f"    Name: {row.name}")
        print(f" Enabled: {'Yes' if row.enabled else 'No'}")
        print(f"Schedule: {row.schedule}")
        print(f"  Params: {row.opts}")
