#----------------------------------------------------------------------
#
# $Id$
#
# Rebuilds the manifest used to keep CDR client files up-to-date.
# Rewrite of original utility by Jeff Holmes 2002-05-14.
#
#----------------------------------------------------------------------
import cdr, sys, time, socket, os, win32file, pywintypes

class File:
    def __init__(self, path, timestamp = None):
        self.name      = path
        self.timestamp = timestamp or self.__getTimestamp()
    def __getTimestamp(self):
        try:
            h = win32file.CreateFile(self.name,
                                     win32file.GENERIC_READ, 0, None,
                                     win32file.OPEN_EXISTING, 0, 0)
            t = win32file.GetFileTime(h)
            h.Close()
            return t[-1].Format("%Y-%m-%dT%H:%M:%S")
        except Exception, e:
            print "failure:", self.name, str(e)
            sys.exit(1)
    def __cmp__(self, other):
        return cmp(self.name, other.name)

def gatherFiles(dirPath):
    files = []
    for name in os.listdir(dirPath):
        thisPath = os.path.join(dirPath, name)
        if os.path.isdir(thisPath):
            files += gatherFiles(thisPath)
        else:
            files.append(File(thisPath))
    return files

def createTicket():
    return u"""\
 <Ticket>
  <Application>%s</Application>
  <Timestamp>%s</Timestamp>
  <Host>%s</Host>
  <Author>%s</Author>
 </Ticket>""" % (sys.argv[0],
                  time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
                  socket.gethostname(), os.environ['USERNAME'])

def createFilelist(files):
    fragmentXml = u" <FileList>\n"
    for f in files:
        fragmentXml += u"""\
  <File>
   <Name>%s</Name>
   <Timestamp>%s</Timestamp>
  </File>
""" % (f.name, f.timestamp)
    return fragmentXml + u" </FileList>"

def writeManifest(manifestXml, manifestTime):
    manifestFile = file(cdr.MANIFEST_PATH, 'w')
    manifestFile.write(manifestXml)
    manifestFile.close()

    timestamp = pywintypes.Time(manifestTime)
    handle = win32file.CreateFile(cdr.MANIFEST_NAME,
                                  win32file.GENERIC_WRITE, 0, None,
                                  win32file.OPEN_EXISTING, 0, 0)
    win32file.SetFileTime(handle, timestamp, timestamp, timestamp)
    handle.Close()

def refreshManifest(where):
    try:
        os.unlink(cdr.MANIFEST_PATH)
    except:
        pass
    os.chdir(where)
    files = gatherFiles('.')
    manifestTime = time.time()
    files.append(File(os.path.join('.', cdr.MANIFEST_NAME),
                      time.strftime("%Y-%m-%dT%H:%M:%S",
                                    time.gmtime(manifestTime))))
    files.sort()
    manifestXml = u"""\
<!-- Timestamps are UTC. -->
<Manifest>
%s
%s
</Manifest>
""" % (createTicket(), createFilelist(files))
    writeManifest(manifestXml.encode('utf-8'), manifestTime)
    result = cdr.runCommand("D:\\cygwin\\bin\\chmod -R 777 *")
    if result.code:
        print "chmod return code: %s" % result.code
        if result.output:
            print result.output

if __name__ == "__main__":
    where = len(sys.argv) > 1 and sys.argv[1] or cdr.CLIENT_FILES_DIR
    refreshManifest(where)
