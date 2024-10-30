#!/usr/bin/env python3

"""Create snapshot of NCI dictionary of cancer terms for CIS requests.

This script generates an HTML page showing all of the English glossary
terms for the patient Cancer.gov dictionary. The input for the script
is the output from dictionary_api_loader.py.

cd ~/repos/scheduler
python -m jobs.dictionary_api_loader.py --tier prod --dump \
  --dictionary glossary > glossary-YYYYMMDD.json
# where YYYYMMDD is the current date
./glossary-snapshot.py < glossary-YYYYMMDD.json > glossary-YYYYMMDD.html
"""

from datetime import date
from functools import cached_property
from json import loads
from sys import stdin
from lxml.html import tostring, builder as B


class Term:
    """Object with term name and plain text definition."""

    STYLE = B.STYLE("""\
* { font-family: "Noto Sans", "Century Gothic", Arial, sans-serif; }
body { margin: 4rem; }
dt { font-weight: bold; color: #2b7bba; page-break-after: avoid; }
dd { color: #2e2e2e; margin-bottom: 1rem; page-break-before: avoid; }
h1 { font-size: 2rem; color: #606060; }
h2 { font-size: 1.5rem; color: #606060; }
""")
    TODAY = date.today()

    def __init__(self, line):
        self.__values = loads(line.strip())

    def __lt__(self, other):
        """Support sorting by term name."""
        return self.name < other.name

    @cached_property
    def definition(self):
        """The string for the term's plain-text definition."""
        return self.__values["definition"]["text"]

    @cached_property
    def in_scope(self):
        """True iff the current record is needed for the report."""
        if self.__values.get("language") != "en":
            return False
        if self.__values.get("dictionary") != "Cancer.gov":
            return False
        return self.__values.get("audience") == "Patient"

    @cached_property
    def name(self):
        """The string for the term's name."""
        return self.__values["term_name"]


terms = []
for line in stdin:
    term = Term(line)
    if term.in_scope:
        terms.append(term)
elements = []
for term in sorted(terms):
    elements.append(B.DT(term.name))
    elements.append(B.DD(term.definition))
page = B.HTML(
    B.HEAD(
        B.META(charset="utf-8"),
        B.TITLE(f"NCI Dictionary of Cancer Terms - {Term.TODAY}"),
        Term.STYLE,
    ),
    B.BODY(
        B.H1("NCI Dictionary of Cancer Terms"),
        B.H2(f"Snapshot taken {Term.TODAY}"),
        B.DL(*elements),
    ),
)
print("<!DOCTYPE html>")
print(tostring(page, pretty_print=True, encoding="unicode"))
