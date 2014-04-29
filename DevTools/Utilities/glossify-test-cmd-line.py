#----------------------------------------------------------------------
#
# $Id$
#
# Tool for checking the health of the glossifier service.  The most common
# cause of failure is someone at cancer.gov trying to connect using a
# temporary URL (on Verdi) I set up for Bryan for a one-time test.
# The correct URL for the service is:
#
#     http://pdqupdate.cancer.gov/u/glossify
#
#----------------------------------------------------------------------
import sys, suds.client
URL = "http://glossifier-stage.cancer.gov/cgi-bin/glossify"
URL = "http://glossifier.cancer.gov/cgi-bin/glossify"
FRAGMENT = (u"<p>Gerota\u2019s capsule breast cancer and mammography "
            u"as well as invasive breast cancer, too</p>")
frag = FRAGMENT
lang = "en"
client = suds.client.Client(URL)
dictionaries = client.factory.create('ArrayOfString')
dictionaries.string.append(u'Cancer.gov')
languages = client.factory.create('ArrayOfString')
languages.string = lang
if type(frag) is not unicode:
    frag = unicode(frag, 'utf-8')
try:
    print client.service.glossify(frag, dictionaries, languages)
except Exception, e:
    print "oops: %s" % e
