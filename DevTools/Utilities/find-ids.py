#!/usr/bin/env python
"""
Report counts for unique values in cdr:id attributes in a CDR document.
"""

import cdr, cdrdb, sys, xml.dom.minidom

if len(sys.argv) < 2:
    sys.stderr.write("usage: find-ids doc-id\n")
    sys.exit(1)
id = cdr.exNormalize(sys.argv[1])
conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
cursor.execute("SELECT xml FROM document WHERE id = ?", id[1])
rows = cursor.fetchall()
if not rows:
    sys.stderr.write("Unable to find %s\n" % sys.argv[1])
    sys.exit(1)
ids = {}
dom = xml.dom.minidom.parseString(rows[0][0].encode('utf-8'))
def findIds(node):
    id = node.getAttribute('cdr:id')
    if id:
        if id in ids:
            ids[id] += 1
        else:
            ids[id] = 1
    for child in node.childNodes:
        if child.nodeType == child.ELEMENT_NODE:
            findIds(child)
findIds(dom.documentElement)
keys = ids.keys()
keys.sort()
for key in keys:
    print("%d %s" % (ids[key], key))
