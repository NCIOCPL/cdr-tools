#!/usr/bin/env python3
"""
Fetch pretty-printed CDR online help page document.
"""

import cdr
import lxml.etree as etree
import os
import sys


def usage():
    print("usage: GetHelpDocForEditing.py CDRID")
    print(" e.g.: GetHelpDocForEditing.py 123456")
    sys.exit(1)


def move_file(filename):
    counter = 1
    newname = "%s.bak-%d" % (filename, counter)
    while os.path.exists(newname):
        counter += 1
        newname = "%s.bak-%d" % (filename, counter)
    try:
        os.rename(filename, newname)
        print("old %s backed up to %s" % (filename, newname))
    except Exception:
        print("unable to rename %s to %s" % (filename, newname))
        sys.exit(1)


if len(sys.argv) != 2:
    usage()
try:
    doc_id = int(sys.argv[1])
except Exception:
    usage()
filename = "%d.xml" % doc_id
if os.path.exists(filename):
    move_file(filename)
doc_obj = cdr.getDoc("guest", doc_id, checkout="N", getObject=True)
parser = etree.XMLParser(remove_blank_text=True)
tree = etree.fromstring(doc_obj.xml, parser)
fp = open(filename, "wb")
fp.write(etree.tostring(tree, encoding="utf-8", pretty_print=True,
                        xml_declaration=True))
fp.close()
print("wrote %s" % filename)
