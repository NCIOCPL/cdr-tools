#----------------------------------------------------------
# Delete references to deleted fragments in Summaries.
# Fixes problems caused by Request4838.py
#----------------------------------------------------------
import sys, re, cdr, ModifyDocs

class Transform:
    def __init__(self, inFname):
        """
        Save input filename from command line.
        """
        self.inFname = inFname
        self.job     = None

        # Pattern for changing SummaryFragmentRef to SummaryRef
        self.refPat = re.compile(r"Summary(?P<fragname>Fragment)Ref")

    def fatal(self, msg):
        msg = "Fatal error: " + msg
        if self.job:
            self.job.log(msg)
        sys.exit(1)

    def getDocIds(self):
        """
        Get doc and fragment ids from input file.  Save them.  Return list
        of source doc ids.
        """
        # Open CSV file of SourceCdrId, TargetCdrId, Fragment
        fp = open(self.inFname)

        chkList = []
        self.fixDocs = {}

        while True:
            line = fp.readline()
            if not line:
                break

            # Parse and save srcId,targId,fragId
            line = line.strip()
            idGroup = line.split(',')
            chkList.append(idGroup)

        # Sort everything
        chkList.sort()

        # Create a hash of source id -> list of pairs of (targ id, frag id)
        for idGroup in chkList:
            srcId  = int(idGroup[0])
            target = (int(idGroup[1]), idGroup[2])

            if not self.fixDocs.has_key(srcId):
                # Create a list of targets for this source with one entry
                self.fixDocs[srcId] = [target,]

            else:
                # Append additional target to existing list
                self.fixDocs[srcId].append(target)

        # Return the source IDs
        keyList = self.fixDocs.keys()
        keyList.sort()
        return keyList

    def run(self, docObj):
        """
        Use regular expressions and string manipulation to fixup the docs
        """
        srcIdStr = docObj.id
        srcId    = cdr.exNormalize(srcIdStr)[1]
        xml      = docObj.xml

        # Get list of targets to fixup for this srcId
        fixups = self.fixDocs[srcId]

        for target in fixups:

            # Full target ID "CDR0000012345#_123"
            targId    = target[0]
            targIdStr = cdr.exNormalize(targId)[0]
            fragIdStr = target[1]

            # Create regex for fragment
            fragPat = r"""ref\w*=\w*['"]%s(?P<frag>#%s)['"]""" % \
                        (targIdStr, fragIdStr)
            pat = re.compile(fragPat)

            # Process all hits
            hits = 0
            pos  = 0
            while True:
                m = pat.search(xml, pos)
                if not m:
                    if hits == 0:
                        self.job.log ("WARNING: %s#%s not found in doc %d" %
                                      (targIdStr, fragIdStr, srcId))
                    break
                hits += 1

                # If this is an external reference to a different doc
                if srcId != targId:
                    # Remove the fragment
                    xml = xml[:m.start('frag')] + xml[m.end('frag'):]

                    # Change SummaryFragmentRef to SummaryRef
                    # Start at right with end tag
                    mfragPat = self.refPat.search(xml, m.end('frag'))
                    if mfragPat:
                        xml = xml[:mfragPat.start('fragname')] + \
                              xml[mfragPat.end('fragname'):]

                    # Same at left end
                    pos = m.start()
                    while xml[pos] != '<':
                        pos -= 1
                    mfragPat = self.refPat.search(xml, pos)
                    if mfragPat:
                        xml = xml[:mfragPat.start('fragname')] + \
                              xml[mfragPat.end('fragname'):]


                # Else it's an internal link
                else:
                    # Remove all the element markup
                    xml = self.squelch(xml, m.start(), srcId)

        # (Almost always) transformed xml
        return xml


    def chgFragRefToRef(self, xml, pos, srcId):
        """
        Change a SummaryFragmentRef to an ordinary SummaryRef.
        """

    def squelch(self, xml, pos, srcId):
        """
        Delete the markup from '<' to '>', inclusive, surounding the passed
        position.

        If there's an end tag, remove it too.

        Pass:
            xml string
            position found by regex
            Source doc id, for error messages

        Return:
            Modified xml string
        """
        # Find start of element
        startPos = pos
        while xml[startPos] != '<':
            startPos -=1

        # Find element tag
        startOpenTag = startPos + 1
        if xml[startOpenTag] == '/':
            startOpenTag += 1
        endOpenTag = startOpenTag
        while xml[endOpenTag] not in (' \t\n'):
            endOpenTag += 1
        tag = xml[startOpenTag:endOpenTag]

        # Find char after end of element start markup
        endPos = endOpenTag
        while xml[endPos] != '>':
            endPos += 1
        endPos += 1

        # Is there a closing tag?
        if xml[endPos - 1] == '/':
            tag = None
        else:
            # Find it
            tagPat = re.compile(r"</%s>" % tag)
            m = tagPat.search(xml, endPos)
            if not m:
                self.fatal("Expecting end tag for %s in docId %d" %
                      (tag, srcId))

            # Compress all end tag markup
            xml = xml[:m.start()] + xml[m.end():]

        # Compress out the starting element markup
        xml = xml[:startPos] + xml[endPos:]

        return xml


#----------------------------------------------------------------------
#   Main
#----------------------------------------------------------------------
if __name__ == "__main__":

    # Args
    if len(sys.argv) < 5:
        print("usage: Request4838FixRefs.py uid pw csvfile test|run {maxdocs}")
        sys.exit(1)
    uid     = sys.argv[1]
    pw      = sys.argv[2]
    csvfile = sys.argv[3]

    # Test / run mode
    testMode = None
    print(sys.argv[4].lower())
    if sys.argv[4].lower() == 'test':
        testMode = True
    elif sys.argv[4].lower() == 'run':
        testMode = False
    else:
        sys.stderr.write('Must specify "test" or "run"')
        sys.exit(1)

    if len(sys.argv) == 6:
        maxdocs = int(sys.argv[5])
    else:
        maxdocs = None

    # Instantiate our object, loading the spreadsheet
    transform = Transform(csvfile)

    # Debug
    # testMode = 'test'

    # Instantiate ModifyDocs job
    job = ModifyDocs.Job(uid, pw, transform, transform,
      'Global change to eliminate references to Purpose sections'
      ' that are going away.  Request 4838.',
      validate=True, testMode=testMode)

    # Install access to job in FilterTransform for logging
    transform.job = job

    # Debug
    if maxdocs:
        job.setMaxDocs(maxdocs)

    # Global change
    job.run()
