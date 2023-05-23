#!/usr/bin/env python

"""Update publishing control documents for a release deployment.
"""

from pathlib import Path
from cdrapi import db
from cdrapi.docs import Doc
from cdrapi.settings import Tier
from cdrapi.users import Session

ACCOUNT = "ReleaseInstaller"
COMMENT = "Updating control document as part of release deployment"
OPTIONS = dict(
    version=True,
    publishable=True,
    comment=COMMENT,
    reason=COMMENT,
    unlock=True,
    val_types=("schema", "links"),
)

tier = Tier()
session = Session.create_session(ACCOUNT, password=tier.password(ACCOUNT))
query = db.Query("document d", "d.id", "d.title")
query.join("doc_type t", "t.id = d.doc_type")
query.where("t.name = 'PublishingSystem'")
for doc_id, doc_title in query.execute().fetchall():
    path = Path(f"{tier.basedir}/Publishing/{doc_title}.xml")
    if path.exists():
        doc = Doc(session, id=doc_id)
        print(f"updating publishing control doc {doc.cdr_id} ({doc.title})")
        doc.check_out(force=True, comment=COMMENT)
        doc.xml = path.read_text(encoding="utf-8")
        doc.save(**OPTIONS)
