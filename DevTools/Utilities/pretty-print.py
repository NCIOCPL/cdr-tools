#!/usr/bin/env python
"""
Use lxml to format an XML document.
"""

import lxml.etree as etree
import sys

if len(sys.argv) < 2:
    source = sys.stdin
else:
    source = sys.argv[1]
parser = etree.XMLParser(remove_blank_text=True)
tree = etree.parse(source, parser)
print(etree.tostring(tree, encoding="utf-8", pretty_print=True))
