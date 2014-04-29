#!/usr/bin/python
#----------------------------------------------------------------------
# $Id$
# Tool for retrieving glossary term pronunciation files posted by CIAT.
#----------------------------------------------------------------------
import paramiko, datetime, sys

audio = "/ciat/Audio/Audio_Transferred"
host = "cancerinfo.nci.nih.gov"
port = 22
uid, pwd = "testftp", "***REMOVED***" # "***REMOVED***"
transport = paramiko.Transport((host, port))
transport.connect(username=uid, password=pwd)
sftp = paramiko.SFTPClient.from_transport(transport)
files = sorted(sftp.listdir(audio))
for f in files:
    print str(sftp.lstat("%s/%s" % (audio, f))).replace("?", f)
for name in sys.argv[1:]:
    fp = sftp.open("%s/%s" % (audio, name))
    bytes = fp.read()
    fp.close()
    fp = open(name, "wb")
    fp.write(bytes)
    fp.close()
    print "fetched %s" % name
sftp.close()
transport.close()
