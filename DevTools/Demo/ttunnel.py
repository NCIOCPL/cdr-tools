#!/usr/bin/env python

"""Demonstrate raw communication with CDR tunneling API.
"""

import requests

url = "https://cdrapi-dev.cancer.gov"
request = """\
<CdrCommandSet>
 <SessionId>guest</SessionId>
 <CdrCommand>
  <CdrGetDoc includeBlob='N'>
   <DocId>CDR0000000070</DocId>
   <Lock>N</Lock>
   <DocVersion>Current</DocVersion>
  </CdrGetDoc>
 </CdrCommand>
</CdrCommandSet>"""
print(requests.post(url, request).text)
