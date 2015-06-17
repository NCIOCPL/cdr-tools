import urllib

url = "https://cdr.dev.cancer.gov/cgi-bin/cdr/https-tunnel.ashx"
request = """\
<CdrCommandSet>
 <SessionId>guest</SessionId>
 <CdrCommand>
  <CdrGetDoc includeBlob='N'>
   <DocId>CDR0000005000</DocId>
   <Lock>N</Lock>
   <DocVersion>Current</DocVersion>
  </CdrGetDoc>
 </CdrCommand>
</CdrCommandSet>"""
conn = urllib.urlopen(url, request)
print conn.read()

