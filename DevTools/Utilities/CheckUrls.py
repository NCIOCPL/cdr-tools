#----------------------------------------------------------------------
#
# $Id$
#
# $Log: not supported by cvs2svn $
#
#----------------------------------------------------------------------

"""\
  Takes a list of URLs from the standard input (or from a named file 
  if there is at least one command-line argument present), one URL on 
  each line, and determines whether the resource identified by the URL 
  is still available.  A report is written to standard output (or 
  appended to a named file if a second command-line argument is present) 
  containing one line for each URL with a problem.  Each line in the 
  report contains three fields, separated by the tab character:

     1. Date and time (local timezone)
     2. The problem detected.
     3. The URL.

  If the URL is malformed, the problem is "Malformed URL".
  If the protocol is not http or https, the problem is "Unexpected protocol".
  If the host does not respond, the problem is "Host not found".
  Otherwise, the problem is the HTTP Status-Code, followed by the HTTP
  Reason-Phrase in parentheses.

  The program remembers hostnames which have not responded to a URL during
  the current run, and avoids trying to connect to the same host for other
  URLs which identify that host later in the run, which should speed up
  the job considerably when we have a lot of URLs for a host which is
  down.
"""

#----------------------------------------------------------------------
# Load the required modules.
#----------------------------------------------------------------------
import sys, httplib, urlparse, socket, time

#----------------------------------------------------------------------
# Extract arguments from the command-line.
#----------------------------------------------------------------------
if len(sys.argv) > 1: sys.stdin = open(sys.argv[1])
if len(sys.argv) > 2: sys.stdout = open(sys.argv[2], "a")

#----------------------------------------------------------------------
# Remember hosts which don't respond so we don't keep trying them.
#----------------------------------------------------------------------
deadHosts = {}

#----------------------------------------------------------------------
# Write out the current time, the problem, and the URL to the log.
#----------------------------------------------------------------------
def report(url, problem):
    now = time.localtime(time.time())
    print "%04d-%02d-%02d %02d:%02d:%02d\t%s\t%s" % (now[0],
                                                     now[1],
                                                     now[2],
                                                     now[3],
                                                     now[4],
                                                     now[5],
                                                     problem,
                                                     url)


#----------------------------------------------------------------------
# Loop through the input, which contains one URL on each line.
#----------------------------------------------------------------------
for url in sys.stdin.readlines():

    # Extract the pieces of the URL
    url = url.strip()
    pieces   = urlparse.urlparse(url)
    host     = pieces[1]
    selector = pieces[2]

    # Check for problems with the URL.
    if not host:
        report(url, "Malformed URL")
        continue
    if deadHosts.has_key(host):
        report(url, "Host not found")
        continue
    if pieces[0] not in ('http','https'):
        report(url, "Unexpected protocol")
        continue

    # Append any trailing portions of the selector.
    if pieces[3]: selector += ";" + pieces[3]
    if pieces[4]: selector += "?" + pieces[4]
    if pieces[5]: selector += "#" + pieces[5]

    # Connect to the host and ask about the resource.
    try:
        http = httplib.HTTP(host)
        http.putrequest('GET', selector)
        http.endheaders()
        reply = http.getreply()
        if reply[0] != 200:
            report(url, "%d (%s)" % (reply[0], reply[1]))
    except IOError, msg:
        report(url, "IOError: %s" % msg)
    except socket.error, msg:
        deadHosts[host] = 1
        report(url, "Host not found")
    except:
        report(url, "Internal error")
