#!/usr/bin/env python

"""Find Insertion/Deletion parents of specific elements.

Useful for figuring out why some elements don't end up in the query_term
table. Indexing a document works on a version of the CDR document which
has had any Insertion and Deletion markup applied at the "published" level.
As fond as the users are of Insertion and Deletion markup, they sometimes
get carried away and use it so heavily that they are unpleasantly surprised
when it get used.
"""

from argparse import ArgumentParser
from sys import stdin
from lxml import etree

def find_markup(node, markup):
    parent = node.getparent()
    if parent is not None:
        if parent.tag in ("Insertion", "Deletion"):
            name = parent.tag
            user = parent.get("UserName") or "???"
            time = parent.get("Time") or "???"
            level = parent.get("RevisionLevel") or "???"
            markup.append(f"{name} user={user} time={time} level={level}")
        find_markup(parent, markup)

parser = ArgumentParser()
parser.add_argument("tag", help="Required name of elements to look for")
opts = parser.parse_args()
root = etree.parse(stdin).getroot()
for node in root.iter(opts.tag):
    markup = []
    find_markup(node, markup)
    if markup:
        print(f"found {node.tag} node, wrapped by:")
        for line in reversed(markup):
            print(f" {line}")
