import argparse
import cdr

values = (
    ("Country", 10, 25),
    ("DIS", 10, 25),
    ("GP", 10, 25),
    ("Glossary", 12, 100),
    ("Media", 8, 100),
    ("Organization", 6, 25),
    ("PoliticalSubUnit", 6, 25),
    ("Summary", 8, 10),
    ("Term", 8, 100)
)
parser = argparse.ArgumentParser()
parser.add_argument("session")
parser.add_argument("--tier")
args = parser.parse_args()
session = args.session
opts = dict(group="Publishing", comment="setting for export concurrency")
if args.tier:
    opts["tier"] = args.tier
for name, processes, batchsize in values:
    opts["name"] = name + "-numprocs"
    opts["value"] = str(processes)
    cdr.updateCtl(session, "Create", **opts)
    opts["name"] = name + "-batchsize"
    opts["value"] = str(batchsize)
    cdr.updateCtl(session, "Create", **opts)
    print(("set {name}={value}".format(**opts)))
