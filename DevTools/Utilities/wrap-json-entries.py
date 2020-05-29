#!/usr/bin/env python

"""Dump sequence of json entries as an array.

Reads from stdin, writes to stdout. The input file has single
json objects, one after the other, as separate objects. The
output file is a single array of those objects.
"""

import json
import sys

entries = []
lines = []
for line in sys.stdin:
    lines.append(line)
    if line == "}\n":
        entries.append(json.loads("".join(lines)))
        lines = []
print(json.dumps(entries, indent=2))
