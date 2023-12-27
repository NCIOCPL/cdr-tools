#!/usr/bin/env python

"""Get one XML document from pub_proc_cg to stdout.

If your document has non-ascii characters in it it may not work well
to try and pipe the output to a tool which expects ascii to be coming
from stdout. Consider instead using the --save option and loading the
encoded document directly into your tool.
"""

from argparse import ArgumentParser
from cdrapi.db import Query

parser = ArgumentParser()
parser.add_argument("id", type=int)
parser.add_argument("--tier")
parser.add_argument("--save", action="store_true")
opts = parser.parse_args()
query = Query("pub_proc_cg", "xml")
query.where(query.Condition("id", opts.id))
row = query.execute().fetchone()
if not row:
    raise Exception(f"CDR{opts.id:d} not found in pub_proc_cg")
if opts.save:
    with open(f"pub_proc_cg-{opts.id:d}.xml", "wb") as fp:
        fp.write(row.xml.encode("utf-8"))
else:
    print(row.xml)
