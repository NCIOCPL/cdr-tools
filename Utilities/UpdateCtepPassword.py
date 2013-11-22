#----------------------------------------------------------------------
#
# $Id$
#
# Install a new password for the service which catches the Organization
# reports we send to CTEP.
#
#----------------------------------------------------------------------
import cdr, sys

if len(sys.argv) != 4:
    sys.stderr.write("usage; UpdateCtepPassword.py cdr-uid cdr-pwd ctep-pwd\n")
    sys.exit(1)
cdr_uid, cdr_pwd, ctep_pwd = sys.argv[1:]
try:
    cdr.updateCtl((cdr_uid, cdr_pwd), "Create", "ctrp", "cred", ctep_pwd,
                  "Used by UploadCtepReport.py")
    print "password update successful"
except Exception, e:
    print "didn't work\n: %s" % e
