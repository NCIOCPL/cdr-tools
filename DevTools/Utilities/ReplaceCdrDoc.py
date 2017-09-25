#!/usr/bin/env python
"""
Store changes to a DOC document from a copy in the file system.
"""

import cdr
import sys

comment = "Replaced by programmer"
if len(sys.argv) == 4:
    session = cdr.login(sys.argv[1], sys.argv[2])
    filename = sys.argv[3]
else:
    session, filename = sys.argv[1:3]
print cdr.repDoc(session, file=filename, val="Y", checkIn="Y"),
