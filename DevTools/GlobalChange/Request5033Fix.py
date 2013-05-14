###########################################################
# Re-add the Gender element to InScopeProtocols that lost it as
# a result of the prior schema / global change filter mismatch.
#
# Command line argument:
#   Name of file containing the CDR IDs of the documents to change.
#     These are derived from the Request5033.py program.
#
#                                               Alan Meyer
#                                               August 2011
# BZIssue::5033
#
# $Id$
#
###########################################################
import sys, lxml.etree as lxml, ModifyDocs


class FixGender:

    def __init__(self, idFileName):
        # Save the passed name of the CDR ID file.
        self.idFile = idFileName
        self.job    = None

    def getDocIds(self):
        # Load IDs
        fp = open(self.idFile)
        idText = fp.read()
        fp.close()

        # Convert them to a list
        idList = idText.split()

        # Convert list strings to integers
        for i in range(len(idList)):
            idList[i] = int(idList[i])

        return idList


    def run(self, docObject):
        # Parse the XML
        tree = lxml.fromstring(docObject.xml)

        # Is this a protocol that was transferred to CTGov?
        if tree.tag == 'CTGovProtocol':
            self.job.log("Doc %s is now a CTGovProtocol - skipping" %
                          docObject.id)
            return docObject.xml

        # Make sure there is no Gender element already present
        genderElems = tree.xpath("./Eligibility/Gender")
        if len(genderElems) > 0:
            self.job.log("Doc %s already has Gender - skipping" %
                          docObject.id)
            return docObject.xml

        # Locate the AgeText element.  It's required.  Gender goes after.
        ageTextElems = tree.xpath("./Eligibility/AgeText")
        if len(ageTextElems) != 1:
            self.job.log("Doc %s has %d AgeText elements - skipping" %
                      (docObject.id, len(ageTextElems)))
            return docObject.xml

        # Create the new element text
        # Analysis program found all Genders = "Both" except one
        genderText = "Both"
        if docObject.id == 65893:
            genderText = "Female"

        # Create element
        genderElem = tree.makeelement("Gender")
        genderElem.text = genderText

        # Append it as a sibling after AgeText
        ageTextElems[0].addnext(genderElem)

        # Return serialization of the modified document
        return lxml.tostring(tree)

if __name__ == "__main__":

    if len(sys.argv) != 5:
        sys.stderr.write(
    "usage: Request5033Fix.py userId pw filename_with_docIds live|test\n")
        sys.exit(1)

    # Get args
    uid, pwd, idFile, runMode = sys.argv[1:]

    # Live or test mode
    if runMode not in ("live", "test"):
        sys.stderr.write('Specify "live" or "test" for run mode\n')
        sys.exit(1)
    if runMode == "test":
        testMode = True
    else:
        testMode = False

    # Debug
    # testMode = True

    # Create the job object
    obj = FixGender(idFile)
    job = ModifyDocs.Job(uid, pwd, obj, obj,
          "Add Gender elements back to InScopeProtocols from which"
          " they were lost, Bugzilla request 5033",
          validate=True, testMode=testMode)

    # So FixGender obj can log
    obj.job = job

    # Debug
    # job.setMaxDocs(3)
    job.run()
