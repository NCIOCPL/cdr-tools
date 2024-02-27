#!/usr/bin/env python

from argparse import ArgumentParser
from pathlib import Path
from lxml import etree
from requests import post

EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
PARMS = "db=pubmed&rettype=medline&retmode=xml&id="

parser = ArgumentParser()
parser.add_argument("pmid")
opts = parser.parse_args()
response = post(EFETCH, data=f"{PARMS}{opts.pmid}")
root = etree.fromstring(response.content)
if root.tag != "PubmedArticleSet":
    print(f"received {root.tag} instead of PubmedArticleSet")
else:
    articles = root.findall("PubmedArticle")
    if len(articles) != 1:
        print(f"received {len(articles)} articles; expecting 1")
    else:
        path = Path(f"{opts.pmid}.xml")
        opts = dict(encoding="utf-8", pretty_print=True)
        path.write_bytes(etree.tostring(articles[0], **opts))
        print(f"wrote {path}")
