#!/usr/bin/env python

"""Save a CDR document using XML in the file system.

Be careful to specify the document ID for an existing document. Otherwise
you will create a second, separate document, which might not be what you
intended.
"""

from argparse import ArgumentParser
from cdrapi.docs import Doc
from cdrapi.users import Session

parser = ArgumentParser()
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("--user", "-u", help="CDR user ID")
group.add_argument("--session", "-s", help="CDR session ID")
parser.add_argument("--xml", "-x", help="document XML", required=True)
parser.add_argument("--doctype", "-d", help="CDR document type", required=True)
parser.add_argument("--id", "-i", help="CDR document ID", type=int)
parser.add_argument("--tier", "-t", help="CDR server tier")
parser.add_argument("--comment", "-c", help="save comment")
parser.add_argument("--version", "-v", help="create version",
                    action="store_true")
parser.add_argument("--publishable", "-p", help="make version publishable",
                    action="store_true")
parser.add_argument("--force", "-f", help="force checkout",
                    action="store_true")
opts = parser.parse_args()
if opts.session:
    session = Session(opts.session, tier=opts.tier)
else:
    session = Session.create_session(opts.user, tier=opts.tier)
print(session)
with open(opts.xml, "rb") as fp:
    xml = fp.read()
doc = Doc(session, id=opts.id, doctype=opts.doctype, xml=xml)
if opts.id:
    doc.check_out(force=opts.force)
version = opts.version or opts.publishable
val_types = ["schema", "links"] if opts.publishable else None
save_opts = dict(
    version=version,
    publishable=opts.publishable,
    val_types=val_types,
    comment=opts.comment,
    unlock=True,
)
doc.save(**save_opts)
print(f"saved {doc.cdr_id} ({doc.title})")
if not opts.session:
    session.logout()
