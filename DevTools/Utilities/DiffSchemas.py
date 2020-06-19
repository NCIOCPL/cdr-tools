#!/usr/bin/env python
#----------------------------------------------------------------------
#
# Compare schemas in working sandbox with those in the CDR.
# Name individual schema files on the command line or use wildcards.
# If no schemas are named, all files ending in ".xml" in the
# current working directory are compared.  If -q is passed on the
# command line (before any file name patterns), then the program
# only identifies which schema files do not match the corresponding
# CDR document and reports errors.
#
#----------------------------------------------------------------------
import cdr, sys, glob, difflib, os.path
from argparse import ArgumentParser
from cdrapi.docs import Doc
from cdrapi.users import Session

differ = difflib.Differ()
parser = ArgumentParser()
parser.add_argument("--quiet", "-q", action="store_true")
parser.add_argument("--tier", "-t")
parser.add_argument("files", nargs="*", default="*.xml")
opts = parser.parse_args()
session = Session('guest', tier=opts.tier)
for pattern in opts.files:
    for name in glob.glob(pattern):
        baseName = os.path.basename(name)
        try:
            with open(name, encoding="utf-8") as fp:
                localDoc = fp.read().replace("\r", "").splitlines(True)
        except Exception as e:
            print(f"... unable to open {name}: {e}")
            continue
        query = f"CdrCtl/Title = {baseName}"
        results = cdr.search(session, query, doctypes=["schema"],
                             tier=opts.tier)
        if len(results) < 1:
            print(f"... schema {baseName} not found in CDR")
        else:
            for result in results:
                if not opts.quiet:
                    print(f"comparing {result.docId} to {name}")
                try:
                    doc = Doc(session, id=result.docId)
                    xml = doc.xml
                except Exception as e:
                    print(f"error: {e}")
                    continue
                cdrDoc = xml.replace("\r", "").splitlines(True)
                diffSeq = differ.compare(localDoc, cdrDoc)
                diff = []
                for line in diffSeq:
                    if line[0] != ' ':
                        diff.append(line)
                diff = "".join(diff)

                # Account for the fact that the final newline is stripped
                # from the schema when it is stored in the CDR
                # XXX Find out where this happens and think about whether
                #     it's appropriate.
                if diff.endswith("+ \n"):
                    diff = diff[:-3]
                if opts.quiet:
                    if diff:
                        print(f"{result.docId} does not match {name}")
                elif diff.strip():
                    print(diff)
