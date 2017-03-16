#!/usr/bin/python
# ********************************************************************
# File name: update-data.py
#            --------------
# Test harness to access PDQ content partner information from the CDR
# ********************************************************************
import urllib2

url = "https://cdr-dev.cancer.gov/cgi-bin/cdr/update-pdq-contact.py"

for action, vendor_id in (("notified", 160),):
    request = "%s?action=%s&id=%s" % (url, action, vendor_id)
    print request
    f = urllib2.urlopen(request)
    print f.read()
