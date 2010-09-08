#----------------------------------------------------------------------
#
# $Id$
#
# Variant of CTGovExport.py created for CTRP.
#
# BZIssue::4896
#
#----------------------------------------------------------------------
import os, sys, xml.dom.minidom, cdr, cdrdb, re, socket, cdrcgi, getopt, time
import xml.sax.saxutils, cdrdocobject, ExcelReader

OUTPUTBASE         = "."
COLLECTION_NAME    = "study_collection.xml"
LOGNAME            = "clinical_trials.log"
TARNAME            = "clinical_trials.tar.bz2"
TARCMD             = "d:\\cygwin\\bin\\tar.exe"
BLOCKPATH          = "/InScopeProtocol/BlockedFromCTGov"
INTERVENTIONS      = "@@INTERVENTIONS-START@@(.*)@@INTERVENTIONS-END@@"
STUDY_DESIGN       = "@@STUDY-DESIGN-START@@(.*)@@STUDY-DESIGN-END@@"
MIDDLE_NAME        = "@@MIDDLE-NAME-START@@(.*?)@@MIDDLE-NAME-END@@"
CTEP_ID            = "@@CTEPID@@(.*?)@@CTEPID@@"
NCTTRIALID         = "@@NCTTRIALID@@"
CTEPTRIALID        = "@@CTEPTRIALID@@"
DCPTRIALID         = "@@DCPTRIALID@@"
TITLES             = "@@TITLES@@"
IS_IND_STUDY       = "@@IS-IND-STUDY@@"
IND_INFO           = "@@IND-INFO@@"
ARM_INFO           = "@@ARM-INFO@@"
REG_INFO           = "@@REG-INFO@@"
RESP_PARTY         = "@@RESP_PARTY@@"
GENDER             = "<gender>Both</gender>"
COMPLETION         = "@@COMPLETION-DATE@@"
VERIFICATION_DATE  = "<verification_date[^>]*>\\d{4}-\\d{2}-\\d{2}</verif"
STATUS             = "<overall_status[^>]*>([^<]*)</overall_status>"
NON_DIGITS         = "[^\\d]"

def escape(me):
    """
    Prepare a string for inclusion in an XML document.
    """
    return me and xml.sax.saxutils.escape(me) or ''

def fixOutcome(o):
    if not o:
        return u""
    return escape(o)

class PostProcess:
    """
    Base class for each of the transformations applied to the
    exported documents.  Public methods:

        setTrial(trial, dom)
            Registers identification information for the trial
            currently being processed, as well as the the XML DOM
            tree for the CDR repository's version of the trial's
            document.

        getWarnings()
            Retrieves a copy of the warning strings collected during
            document transformation and clears out the list of those
            warnings.

        clearWarnings()
            Clears out the list of warnings collected during document
            transformation.

        addWarning(warning)
            Records a warning message for subsequent logging by the
            JobControl object.

        getDerivedClasses()
            Finds all classes derived from this base class, regardless
            of the module in which the derived classes were defined.
            This allows the JobControl object to apply transformations
            without having an explicitly coded list of the transformation
            classes.

    Derived class must also implement the class method getPattern(), which
    returns the regular expression object to find portions of the trial
    documents which must be replaced by the transformation, and the static
    method convert(match), which returns the replacement for each such
    portion.
    """

    __warnings = []

    @classmethod
    def setTrial(cls, trial, dom):
        cls.trial  = trial
        cls.cdrDom = dom

    @classmethod
    def getWarnings(cls):
        warnings = tuple(cls.__warnings)
        cls.clearWarnings()
        return warnings

    @classmethod
    def clearWarnings(cls):
        # Don't assign cls.__warnings = [], which would create a separate
        # __warnings attribute for the derived class, leaving the list
        # retrieved by getWarnings() untouched.
        while cls.__warnings:
            cls.__warnings.pop()

    @classmethod
    def addWarning(cls, warning):
        cls.__warnings.append(warning)

    @classmethod
    def getDerivedClasses(cls):
        children = []
        moduleNames = sys.modules.keys()
        for moduleName in moduleNames:
            module = sys.modules[moduleName]

            # The encodings 'modules' don't really exist.
            if module:
                memberNames = module.__dict__.keys()
                for memberName in memberNames:
                    try:
                        # Try block just in case dictionary shifts under
                        # our feet.
                        member = module.__dict__[memberName]
                        # Try block also catches members which aren't classes.
                        if member is not cls and issubclass(member, cls):
                            children.append(member)
                    except:
                        pass
        return children

    @classmethod
    def getPattern(cls):
        raise Exception("%s must implement getPattern() method" % cls)

    @staticmethod
    def convert(match):
        raise Exception("derived class must implement convert() method")

class Intervention(PostProcess):
    """
    Transformation to convert all of the original document's
    Intervention elements to the structure specified by NLM's
    DTD, based on the semantic types of the terms found in the
    Intervention elements.  Implemented as a post-process since
    the XSL/T filter which is fed the vendor XML document must
    retrieve the semantic type information from the CDR, as it
    is not exported with the vendor document.
    """
    
    __pattern                = re.compile(INTERVENTIONS, re.DOTALL)
    __termSemanticTypes      = {}
    __termNames              = {}
    __ctGovInterventionTypes = {}
    __conn                   = cdrdb.connect('CdrGuest')
    __mappings               = {}
    __interventionNameDocs   = set()

    def __init__(self, node):
        cdrRef             = node.getAttribute('cdr:ref')
        self.docId         = JobControl.extractIntId(cdrRef)
        self.name          = Intervention.getTermName(self.docId)
        self.semanticTypes = self.__getSemanticTypes(self.docId)
        self.ctGovIntType  = self.getCtGovInterventionType(cdrRef)
        self.__interventionNameDocs.add(self.docId)

    @classmethod
    def getMappings(cls):
        return cls.__mappings

    @classmethod
    def getInterventionNameDocs(cls):
        return cls.__interventionNameDocs

    @classmethod
    def getTermName(cls, docId):
        if not docId:
            raise Exception("Intervention.getTermName(): no docId supplied")
        name = cls.__termNames.get(docId)
        if name is None:
            dom = JobControl.getVendorDoc(docId)
            if not dom:
                raise Exception("Intervention.getTermName(%s): "
                                "term not published" % docId)
            for node in dom.documentElement.childNodes:
                if node.nodeName == 'PreferredName':
                    name = cdr.getTextContent(node).strip()
                    if name:
                        cls.__termNames[docId] = name
                        return name
            if not name:
                raise Exception("No name found for term CDR%s" % docId)
        return name
        
    @classmethod
    def getCtGovInterventionType(cls, docId):
        if not docId:
            raise Exception("Intervention.getCtGovInterventionType(): "
                            "no docId supplied")
        docId = JobControl.extractIntId(docId)
        ctGovInterventionType = cls.__ctGovInterventionTypes.get(docId)
        if ctGovInterventionType is None:
            cursor = cls.__conn.cursor()
            cursor.execute("""\
                SELECT value
                  FROM query_term_pub
                 WHERE path = '/Term/CTGovInterventionType'
                   AND doc_id = ?""", docId)
            rows = cursor.fetchall()
            cursor.close()
            ctGovInterventionType = rows and rows[0][0] or None
            cls.__ctGovInterventionTypes[docId] = ctGovInterventionType
        #if not ctGovInterventionType:
        #    raise Exception("no CTGovInterventionType for %s" % docId)
        return ctGovInterventionType
        
    @classmethod
    def getPattern(cls):
        return cls.__pattern

    @staticmethod
    def convert(match):
        """
        For mapping logic, see mapping.xls (Lakshmi Grama, 2002-12-12,
        revised 2002-12-13), attached to issue #1892 with comment #42.
        Intervention type parents suppressed 2007-10-24 at Lakshmi's
        request.  Further revision of the mapping logic posted by Lakshmi
        2008-05-18 with comment #43 of issue #4076.

        RMK (2008-11-26): mapping logic completely rewritten; see
        issue 4367.
        """

        # Needed for new FDAAA requirements.
        nodes = Intervention.cdrDom.getElementsByTagName('ArmOrGroupLabel')
        armLabels = set([cdr.getTextContent(node) for node in nodes])

        # Collect information for unique intervention type/name combinations.
        trialDocId = Intervention.trial.cdrId
        outputBlocks = {}
        for node in Intervention.cdrDom.getElementsByTagName('Intervention'):
            interventionType        = None
            ctGovInterventionType   = None
            interventionDescription = None
            specificInterventions   = []
            armOrGroupLinks         = set()
            interventionTypeDocId   = None
            for child in node.childNodes:
                if child.nodeName == "InterventionNameLink":
                    specificInterventions.append(Intervention(child))
                elif child.nodeName == "InterventionType":
                    cdrRef = child.getAttribute('cdr:ref')
                    interventionTypeDocId = cdrRef
                    typeName = Intervention.getTermName(cdrRef)
                    if typeName:
                        interventionType = typeName
                    typeName = Intervention.getCtGovInterventionType(cdrRef)
                    if typeName:
                        ctGovInterventionType = typeName
                elif child.nodeName == "InterventionDescription":
                    desc = cdr.getTextContent(child).strip()
                    if desc:
                        interventionDescription = desc
                elif child.nodeName == "ArmOrGroupLink":
                    link = cdr.getTextContent(child)
                    if link not in armLabels:
                        raise Exception(u"unmatched ArmOrGroupLink "
                                        u"'%s'" % link)
                    armOrGroupLinks.add(link)

            # If we have ArmOrGroup blocks but no ArmOrGroupLinks to them
            # in this Intervention block, we avoid sending anything from
            # the block, because that makes CT.gov unhappy.
            if armOrGroupLinks or not armLabels:

                # CT.gov will complain if we send arm info but no description.
                if armLabels and not interventionDescription:
                    raise Exception(u"missing intervention description")

                for intervention in specificInterventions:

                    semanticTypes = intervention.semanticTypes
                    if "Drug/agent combination" not in semanticTypes:

                        if not intervention.ctGovIntType:
                            raise Exception("missing CT.gov intervention "
                                            "type for CDR%s" %
                                            intervention.docId)
                        exportType = intervention.ctGovIntType
                        name = intervention.name
                        desc = armLabels and interventionDescription or None
                        key = (exportType, name)
                        block = outputBlocks.get(key)
                        if not block:
                            block = Intervention.OutputBlock(interventionType,
                                                             intervention.name,
                                                             exportType, name,
                                                             desc,
                                                             intervention.docId)
                            outputBlocks[key] = block
                        block.armOrGroupLabels |= armOrGroupLinks

                if not specificInterventions:
                    if interventionType and ctGovInterventionType:
                        n = interventionType
                        t = ctGovInterventionType
                        d = armLabels and interventionDescription or None
                        i = JobControl.extractIntId(interventionTypeDocId)
                        key = (t, n)
                        block = outputBlocks.get(key)
                        if not block:
                            block = Intervention.OutputBlock(interventionType,
                                                             None, t, n, d, i)
                            outputBlocks[key] = block
                        block.armOrGroupLabels |= armOrGroupLinks

        # Lakshmi has requested an additional processing step here, to
        # use a hierarchy of CT.gov intervention types to ensure that
        # only one intervention is exported per intervention_name value
        # for a given trial.  We are hard-wiring the hierarchy in the
        # code, rather than implementing a more data-driven approach,
        # because we don't anticipate using this program much longer.
        # First we collect all the intervention blocks with the same
        # intervention name.
        # 2008-01-14: Lakshmi has asked that we modify this step,
        # avoiding the attempt to pick a preferred block when there
        # are two or more intervention blocks with the same name
        # but different types, and instead fail the export of the
        # trial when this condition exists.
        interventions = {}
        for key in outputBlocks:
            block = outputBlocks[key]
            if block.interventionName not in interventions:
                interventions[block.interventionName] = []
            interventions[block.interventionName].append(block)

        # Now we pick the block we prefer for each name.  It is an
        # error if the hierarchy does not select a single block
        # when more than one block exists for a given intervention
        # name.
        # 2008-01-14: modified to reject any trial which has two
        # or more intervention blocks with the same intervention
        # name, without any attempt to pick a preferred block.
        uniqueBlocks = []
        for name in interventions:
            blocks = interventions[name]
            if len(blocks) == 1:
                uniqueBlocks.append(blocks[0])
            else:
                error = (u"intervention '%s' has multiple types %s" %
                         (name, u"; ".join([(u"'%s'" % b.interventionType)
                                            for b in blocks])))
                raise Exception(error)
        uniqueBlocks.sort()

        # Create the output.
        interventions = []
        for block in uniqueBlocks:
            interventions.append(u"""\
  <intervention cdr-id='CDR%010d'>
    <intervention_type>%s</intervention_type>
    <intervention_name>%s</intervention_name>
""" % (block.cdrId, block.interventionType, escape(block.interventionName)))
            if block.interventionDesc:
                interventions.append(u"""\
    <intervention_description>
      <textblock>%s</textblock>
    </intervention_description>
""" % escape(block.interventionDesc))
            labels = list(block.armOrGroupLabels)
            labels.sort()
            for label in labels:
                interventions.append(u"""\
    <arm_group_label>%s</arm_group_label>
""" % escape(label))
            interventions.append(u"""\
  </intervention>
""")

            # Remember the mapping in case we're debugging the job.
            key = (block.originalType, block.originalName,
                   block.interventionType, block.interventionName)
            if key not in Intervention.__mappings:
                Intervention.__mappings[key] = []
            Intervention.__mappings[key].append(trialDocId)

        return u"".join(interventions) + u"  "

    @classmethod
    def __getSemanticTypes(cls, docId):
        if not docId:
            return set()
        semanticTypes = cls.__termSemanticTypes.get(docId)
        if semanticTypes is None:
            semanticTypes = set()
            dom = JobControl.getVendorDoc(docId)
            if dom:
                for node in dom.documentElement.childNodes:
                    if node.nodeName == 'SemanticType':
                        typeName = cdr.getTextContent(node).strip()
                        if typeName:
                            semanticTypes.add(typeName)
            cls.__termSemanticTypes[docId] = semanticTypes
        return semanticTypes

    class OutputBlock:
        def __init__(self, oType, oName, iType, iName, iDesc=None, cdrId=None):
            self.originalType     = oType
            self.originalName     = oName
            self.interventionType = iType
            self.interventionName = iName
            self.interventionDesc = iDesc
            self.cdrId            = cdrId
            self.armOrGroupLabels = set()
        def __cmp__(self, other):
            return cmp((self.interventionType, self.interventionName),
                       (other.interventionType, other.interventionName))

class StudyDesignInfo(PostProcess):
    """
    Creates the study_design element required by NLM's DTD.  This
    transformation has to be implemented as a post-process because
    it relies on the StudyCategory block in the CDR document,
    which is not exported with the published vendor output.
    """

    __pattern  = re.compile(STUDY_DESIGN, re.DOTALL)
    __mappings = { u"allocation": { u"RANDOMIZED":         u"Randomized",
                                    u"NON-RANDOMIZED":     u"Non-Randomized" },
                   u"masking":    { u"OPEN LABEL":         u"Open Label",
                                    u"SINGLE BLIND":       u"Single Blind",
                                    u"DOUBLE BLIND":       u"Double Blind" },
                   u"control":    { u"PLACEBO-CONTROLLED": u"Placebo Control",
                                    u"CONTROLLED":         u"Active Control",
                                    u"UNCONTROLLED":       u"Uncontrolled" }}
    __interventional = { u'TREATMENT':                     u'Treatment',
                         u'SCREENING':                     u'Screening',
                         u'PREVENTION':                    u'Prevention',
                         u'DIAGNOSTIC':                    u'Diagnostic',
                         u'SUPPORTIVE CARE':               u"Supportive care",
                         u'EDUCATIONAL/COUNSELING/TRAINING':
                                           u'Educational/Counseling/Training',
                         u'HEALTH SERVICES RESEARCH':
                                           u'Health services research' }
    __observational = { u'NATURAL HISTORY/EPIDEMIOLOGY':   u'Natural History',
                        u'BEHAVIORAL STUDY':               u'Psychosocial',
                        u'PSYCHOSOCIAL':                   u'Psychosocial',
                        u'GENETICS':                       u'Natural History' }
    __mappableStudyCategories = set(__interventional.keys() +
                                    __observational.keys())
                   
    @classmethod
    def getPattern(cls):
        return cls.__pattern

    @classmethod
    def __isSingleArmOrGroupStudy(cls):
        for node in cls.cdrDom.getElementsByTagName('ArmsOrGroups'):
            if node.getAttribute('SingleArmOrGroupStudy') == 'Yes':
                return True
        return False
        
    @staticmethod
    def convert(match):
        """
        See item 20 of the document attached with comment #14 for
        CDR Bugzilla issue #1892 for the logic used for this mapping,
        as well as the modification to the logic in comment #43 in
        the same issue.
        """
        fragment = match.group(1)
        try:
            dom = xml.dom.minidom.parseString(fragment.encode('utf-8'))
        except:
            f = open('fragment.xml', 'wb')
            f.write(fragment)
            f.close()
            raise
        docElem = dom.documentElement
        studyDesignValues = {}
        primaryOutcomes   = []
        secondaryOutcomes = []

        # Collect StudyDesign and Outcome values from the filtered document.
        # RMK (2007-12-19): need to get the Outcome information from the
        # original CDR document, at least until the Safety attribute has
        # been exported with the vendor data.
        for child in docElem.childNodes:
            if child.nodeName == 'StudyDesign':
                value = cdr.getTextContent(child).strip()
                if value:
                    studyDesignValues[value.upper()] = value

        # We now need to know the study type here, because research
        # studies get special treatment (see comment #9 in tracking
        # system issue #4532).
        studyType = None
        isResearchStudy = False
        dom = StudyDesignInfo.cdrDom
        for child in dom.documentElement.childNodes:
            if child.nodeName == 'ProtocolDetail':
                for grandchild in child.childNodes:
                    if grandchild.nodeName == 'StudyType':
                        studyType = cdr.getTextContent(grandchild).strip()
                        if studyType.upper() == 'RESEARCH STUDY':
                            isResearchStudy = True

        # Find the primary study category from the original CDR document.
        studyCategory = None
        secondaryCategories = []
        for node in dom.getElementsByTagName('StudyCategory'):
            studyCategoryType = None
            studyCategoryName = None
            for child in node.childNodes:
                if child.nodeName == 'StudyCategoryType':
                    studyCategoryType = cdr.getTextContent(child).strip()
                elif child.nodeName == 'StudyCategoryName':
                    studyCategoryName = cdr.getTextContent(child).strip()
            if studyCategoryName:
                if studyCategoryType == 'Primary':
                    studyCategory = studyCategoryName.upper()
                else:
                    secondaryCategories.append(studyCategoryName.upper())

        # Get Outcome from the CDR document as well (see comment above).
        for node in dom.getElementsByTagName('Outcome'):
            value = cdr.getTextContent(node).strip()
            if value:
                outcomeType = node.getAttribute('OutcomeType')
                safety = node.getAttribute('Safety').lower()
                if outcomeType == 'Primary':
                    primaryOutcomes.append((value, safety))
                elif outcomeType == 'Secondary':
                    secondaryOutcomes.append((value, safety))

        # Start building the replacement output.
        designXml = [u"""
  <study_design>
"""]

        # Modification added by Lakshmi 2006-09-21 in comment #100
        # of Bugzilla request #1892:
        #
        # One last tweak (famous last words!)
        # While generating the following element
        # - <interventional_design>
        # <interventional_subtype>
        # could you add an additional conditional check
        #
        # if mapping from the first
        # <StudyCategory>
        # <StudyCategoryName>
        # value to the value for <interventional_subtype> in CTGOV fails,
        # then proceed to the next <StudyCategoryName> value and map.
        # Repeat if needed. If no mapping is found generate an error
        # message
        if not isResearchStudy:
            if studyCategory not in StudyDesignInfo.__mappableStudyCategories:
                for c in secondaryCategories:
                    if c in StudyDesignInfo.__mappableStudyCategories:
                        studyCategory = c
                        break
            if studyCategory not in StudyDesignInfo.__mappableStudyCategories:
                trial = StudyDesignInfo.trial
                print "doc=%s/%s studyCategory=%s" % (trial.cdrId,
                                                      trial.docVersion,
                                                      studyCategory)
                raise Exception("no match for study category '%s' found" %
                                studyCategory)

        # For new elements required by issue #4076.
        arms = StudyDesignInfo.cdrDom.getElementsByTagName('ArmOrGroup')
        
        # If the value we got from the original CDR document matches one
        # of the keys in the __interventional dictionary (see top of class
        # definition), then we set the study_type to 'interventional' and
        # insert an interventional_design element as a child of study_design.
        if not isResearchStudy:
            if studyCategory in StudyDesignInfo.__interventional:

                # Create a dictionary to be used to fill in the placeholders
                # below for the top of the interventional_design element.
                elements = { u"interventional_subtype":
                             u"<interventional_subtype>%s"
                             "</interventional_subtype>"
                             % StudyDesignInfo.__interventional[studyCategory]
                           }
                for element, mapping in StudyDesignInfo.__mappings.items():
                    value = None
                    for key in mapping:
                        if key in studyDesignValues:
                            value = mapping[key]
                            break
                    if value:
                        elements[element] = u"<%s>%s</%s>" % (element, value,
                                                              element)
                    else:
                        elements[element] = u"<%s/>" % element
                element = u"number_of_arms"

                if arms:
                    elements[element] = u"<%s>%d</%s>" % (element, len(arms),
                                                          element)
                elif StudyDesignInfo.__isSingleArmOrGroupStudy():
                    elements[element] = u"<%s>1</%s>" % (element, element)
                else:
                    elements[element] = u"<%s/>" % element

                designXml.append(u"""\
    <study_type>interventional</study_type>
    <interventional_design>
      %(interventional_subtype)s
      %(allocation)s
      %(masking)s
      %(control)s
      <assignment/>
      <endpoint/>
      %(number_of_arms)s
    </interventional_design>
""" % elements)

        # If the primary study design value (from the original CDR
        # document for the protocol) matches one of the keys in the
        # __observational dictionary (see the top of the class
        # definition), then we set the study_type to 'observational'
        # and insert an observational_design element as a child of
        # the study_design element.  We have to use empty elements
        # for many of the children of observational_design, because
        # although they are all required, we don't have mapping
        # instructions for most of them.
        #
        # 2009-03-23 (RMK): we no longer include the observational_design
        # block (see comment #9 in issue #4532).
        if isResearchStudy or studyCategory in StudyDesignInfo.__observational:
            designXml.append(u"""\
    <study_type>observational</study_type>
""")

        # Finish off the replacement XML fragment and return it.
        # 2007-10-10: Lakshmi has instructed us to move the outcome
        # elements outside of (and following) the study_design
        # element.
        designXml.append(u"""\
  </study_design>
""")

        # Outcome elements are now top-level.
        for outcome, safety in primaryOutcomes:
            designXml.append(u"""\
  <primary_outcome>
    <outcome_measure>%s</outcome_measure>
    <outcome_safety_issue>%s</outcome_safety_issue>
  </primary_outcome>
""" % (fixOutcome(outcome), safety))
        for outcome, safety in secondaryOutcomes:
            designXml.append(u"""\
  <secondary_outcome>
    <outcome_measure>%s</outcome_measure>
    <outcome_safety_issue>%s</outcome_safety_issue>
  </secondary_outcome>
""" % (fixOutcome(outcome), safety))

        # We're done.
        return u"".join(designXml)

class MiddleInitials(PostProcess):
    """
    Processing to replace middle names with middle initials.
    Implemented as a post-processing routine because regular
    expression support is only a 'future enhancement' in the
    XSL/T world.
    """

    __middleInitialsPattern = re.compile(MIDDLE_NAME, re.DOTALL)
    __multidotPattern       = re.compile(u"\\.\\.+",  re.DOTALL)
    __multispacePattern     = re.compile(u"\\s+")

    @classmethod
    def getPattern(cls):
        return cls.__middleInitialsPattern

    def __init__(self, original):
        self.original = original
        self.fixed    = self.original.strip()
        self.fixed    = self.__multispacePattern.sub(u" ", self.fixed)
        self.fixed    = self.__multidotPattern.sub(u".", self.fixed)
        self.fixed    = self.fixed.replace(u"\"", u"")
        if not self.__isInitials():
            self.fixed = self.__makeInitials()

    def __makeInitials(self):
        words = self.fixed.split()
        if words[0] == u'St.':
            return u'S.'
        sep = u''
        newWords = []
        for word in words:
            if word[0].isupper():
                newWords.append(word[0] + u'.')
            elif word[0] != '(':
                sep = u' '
                newWords.append(word)
        return sep.join(newWords)

    def __isInitials(self):
        fixed = self.fixed
        if len(fixed) <= 3 and fixed.isalpha() and fixed.isupper():
            return True
        while fixed:
            if fixed[0] == u' ':
                fixed = fixed[1:]
            if len(fixed) < 2 or not fixed[0].isupper():
                return False
            if fixed[1] == u'h' and len(fixed) > 2 and fixed[2] == u'.':
                fixed = fixed[3:]
            else:
                if fixed[1] != u'.':
                    return False
                fixed = fixed[2:]
        return True

    @staticmethod
    def convert(match):
        """
        See Bugzilla CDR issue #1734 for the discussion of the
        requirements for this transformation.
        """
        mi = MiddleInitials(match.group(1))
        return escape(mi.fixed)

class Titles(PostProcess):
    """
    Collect the titles needed for the brief_title and official_title
    elements of the document exported to NLM.  Implemented as a post-
    processing transformation because the vendor document does not
    always contain the original title.
    """

    __pattern = re.compile(TITLES)

    @classmethod
    def getPattern(cls):
        return cls.__pattern

    @staticmethod
    def convert(match):
        """
        See the discussion of the requirements for this transformation
        in comments throughout CDR Bugzilla issue #1892.
        """
        patientTitle      = None
        professionalTitle = None
        originalTitle     = None
        for node in Titles.cdrDom.documentElement.childNodes:
            if node.nodeName == 'ProtocolTitle':
                title     = cdr.getTextContent(node).strip()
                titleType = node.getAttribute('Type').strip()
                if title and titleType:
                    if titleType == 'Professional':
                        professionalTitle = title
                    elif titleType == 'Patient':
                        patientTitle = title
                    elif titleType == 'Original':
                        originalTitle = title
        titles = [u"""
  <brief_title>%s</brief_title>
""" % escape(patientTitle)]
        if originalTitle or professionalTitle:
            titles.append(u"""\
  <official_title>%s</official_title>
""" % (originalTitle and escape(originalTitle) or escape(professionalTitle)))
        return u"".join(titles)

class IsIndStudy(PostProcess):
    """
    Fills in the correct value for the exported is_ind_study element,
    indicating whether the study is involved in the FDA's Investigational
    New Drug (IND) application process.  The values allowed by NLM's
    DTD are 'none' (meaning we don't know), 'yes' and 'no'.  If the
    FDAINDInfo element is present in the original CDR document, we
    insert 'yes'; otherwise 'none'.  The FDAINDInfo block is not
    preserved in the vendor output, so we must use a post-processing
    routine to determine the correct value.
    """

    __pattern = re.compile(IS_IND_STUDY)

    @classmethod
    def getPattern(cls):
        return cls.__pattern

    @staticmethod
    def convert(match):
        for node in IsIndStudy.cdrDom.documentElement.childNodes:
            if node.nodeName == 'FDAINDInfo':
                return u'yes'
        return u'none'

class IndInfo(PostProcess):
    """
    Fills in the correct values for the exported ind_info element,
    using the information in the original CDR document's FDAINDInfo
    section (which is not exported in the vendor filter, hence the
    need for post processing).  Note that the INDSerialNumber is
    optional in the CDR schema for InScopeProtocol documents, but
    the corresponding ind_serial_number is required by NLM's DTD.
    """

    __pattern = re.compile(IND_INFO)

    @classmethod
    def getPattern(cls):
        return cls.__pattern

    @staticmethod
    def convert(match):
        """
        See the mapping in Lakshmi's spreadsheet, attached to issue
        #1892 with comment #42.
        """
        indGrantor      = u''
        indNumber       = u''
        indSerialNumber = u''
        found           = False
        for node in IndInfo.cdrDom.documentElement.childNodes:
            if node.nodeName == 'FDAINDInfo':
                found = True
                for child in node.childNodes:
                    if child.nodeName == 'INDGrantor':
                        indGrantor = cdr.getTextContent(child).strip()
                    elif child.nodeName == 'INDNumber':
                        indNumber = cdr.getTextContent(child).strip()
                    elif child.nodeName == 'INDSerialNumber':
                        indSerialNumber = cdr.getTextContent(child).strip()
        if found:
            return u"""
  <ind_info>
    <ind_grantor>%s</ind_grantor>
    <ind_number>%s</ind_number>
    <ind_serial_number>%s</ind_serial_number>
  </ind_info>""" % (escape(indGrantor), escape(indNumber),
                    escape(indSerialNumber))
        else:
            return u""

class ArmInfo(PostProcess):
    """
    Adds information about protocol arm groups in the protocol, as requested
    by tracker issue #4076.
    """

    __pattern = re.compile(ARM_INFO)

    @classmethod
    def getPattern(cls):
        return cls.__pattern

    @staticmethod
    def convert(match):
        """
        See the mapping in Lakshmi's spreadsheet, attached to issue
        #1892 with comment #42.
        """

        replacement = []
        indGrantor      = u''
        indNumber       = u''
        indSerialNumber = u''
        found           = False
        for node in ArmInfo.cdrDom.getElementsByTagName('ArmOrGroup'):
            armLabel = armType = armDesc = u""
            for child in node.childNodes:
                if child.nodeName == 'ArmOrGroupLabel':
                    armLabel = cdr.getTextContent(child).strip()
                elif child.nodeName == 'ArmOrGroupType':
                    armType = cdr.getTextContent(child).strip()
                elif child.nodeName == 'ArmOrGroupDescription':
                    armDesc = cdr.getTextContent(child).strip()
            replacement.append(u"""\
  <arm_group>
   <arm_group_label>%s</arm_group_label>
   <arm_type>%s</arm_type>
   <arm_group_description><textblock>%s</textblock></arm_group_description>
  </arm_group>
""" % (escape(armLabel), escape(armType), escape(armDesc)))
        return u"".join(replacement)

class FixGender(PostProcess):
    """
    Replaces gender element with value reflecting the Gender element
    of the CDR document.  Eventually we'll be able to get this
    from the vendor XML, but it's not there right now.
    """

    __pattern = re.compile(GENDER)

    @classmethod
    def getPattern(cls):
        return cls.__pattern

    @staticmethod
    def convert(match):
        for node in FixGender.cdrDom.getElementsByTagName('Gender'):
            return u"<gender>%s</gender>" % cdr.getTextContent(node).strip()
        return u"<gender>Both</gender>"

class CompletionDate(PostProcess):
    """
    Pulls in the new CompletionDate value to comply with new
    legislative requirements.
    """

    __pattern = re.compile(COMPLETION)

    @classmethod
    def getPattern(cls):
        return cls.__pattern

    @staticmethod
    def convert(match):
        dom = CompletionDate.cdrDom
        date = u""
        dateType = u""
        for node in dom.getElementsByTagName('CompletionDate'):
            date = cdr.getTextContent(node).strip()
            dateType = node.getAttribute('DateType')
            if date and dateType:
                break
        if dateType == 'Projected':
            dateType = 'Anticipated'
        if date:
            date = date
        result = u"""
  <primary_compl_date>%s</primary_compl_date>
  <primary_compl_date_type>%s</primary_compl_date_type>
  """ % (date, dateType)
        trial = CompletionDate.trial
        return result

class RegulatoryInfo(PostProcess):
    """
    Inserts is_fda_regulated, is_section_801, and delayed_posting elements.
    """

    __pattern = re.compile(REG_INFO)

    @classmethod
    def getPattern(cls):
        return cls.__pattern

    @staticmethod
    def convert(match):

        dom            = RegulatoryInfo.cdrDom
        isFdaRegulated = None
        isSection801   = None
        delayedPosting = None
        result         = [u"\n  "]
        for node in RegulatoryInfo.cdrDom.documentElement.childNodes:
            if node.nodeName == 'RegulatoryInformation':
                for child in node.childNodes:
                    if child.nodeName == 'FDARegulated':
                        isFdaRegulated = cdr.getTextContent(child).lower()
                    elif child.nodeName == 'Section801':
                        isSection801 = cdr.getTextContent(child).lower()
                    elif child.nodeName == 'DelayedPosting':
                        delayedPosting = cdr.getTextContent(child).lower()
        if isFdaRegulated:
            result.append(u"""\
<is_fda_regulated>%s</is_fda_regulated>
  """ % isFdaRegulated)
            if isFdaRegulated == 'yes' and isSection801:
                result.append(u"""\
<is_section_801>%s</is_section_801>
  """ % isSection801)
                if isSection801 == 'yes' and delayedPosting:
                    result.append(u"""\
<delayed_posting>%s</delayed_posting>
  """ % delayedPosting)
        return u"".join(result)

class ResponsibleParty(PostProcess):
    """
    Inserts and populates the resp_party element block.
    """

    __pattern = re.compile(RESP_PARTY)
    __conn = cdrdb.connect('CdrGuest')

    @classmethod
    def getPattern(cls):
        return cls.__pattern

    @staticmethod
    def getPersonFragId(ids, docId, conn):
        if ids[2]:
            return ids[2]
        return cdrdocobject.Person.getCipsContactId(docId, conn)

    @staticmethod
    def getOrgFragId(ids, docId, conn):
        if ids[2]:
            return ids[2]
        return cdrdocobject.Organization.getCipsContactId(docId, conn)

    @staticmethod
    def convert(match):
        
        result = [u"\n  "]
        conn = ResponsibleParty.__conn
        cursor = conn.cursor()
        dom = ResponsibleParty.cdrDom
        nameTitle = org = phone = email = ctepPid = ctepOid = None
        for node in dom.getElementsByTagName('ResponsiblePerson'):
            linkString = None
            for child in node.getElementsByTagName('Person'):
                linkString = child.getAttribute('cdr:ref')
            for child in node.getElementsByTagName('SpecificPhone'):
                phone = cdr.getTextContent(child).strip()
            for child in node.getElementsByTagName('SpecificEmail'):
                email = cdr.getTextContent(child).strip()
            if linkString:
                ids     = cdr.exNormalize(linkString)
                docId   = ids[1]
                ctepPid = JobControl.getCtepId(docId)
                fragId  = ResponsibleParty.getPersonFragId(ids, docId, conn)
                filt    = 'Person Contact Fragment With Name'
                contact = cdrdocobject.Person.Contact(docId, fragId, filt)
                name    = contact.getPersonalName()
                orgs    = contact.getOrgs()
                phone   = phone or contact.getPhone()
                email   = email or contact.getEmail()
                if name:
                    nameTitle = name.format(useSuffixes = False,
                                            usePrefix = False)
                if orgs:
                    org = orgs[0]
        for node in dom.getElementsByTagName('ResponsibleOrganization'):
            linkString = None
            for child in node.getElementsByTagName('Organization'):
                linkString = child.getAttribute('cdr:ref')
            for child in node.getElementsByTagName('SpecificPhone'):
                phone = cdr.getTextContent(child).strip()
            for child in node.getElementsByTagName('SpecificEmail'):
                email = cdr.getTextContent(child).strip()
            for child in node.getElementsByTagName('PersonTitle'):
                nameTitle = cdr.getTextContent(child).strip()
            if linkString:
                ids     = cdr.exNormalize(linkString)
                docId   = ids[1]
                fragId  = ResponsibleParty.getOrgFragId(ids, docId, conn)
                contact = cdrdocobject.Organization.Contact(docId, fragId)
                orgs    = contact.getOrgs()
                phone   = phone or contact.getPhone()
                email   = email or contact.getEmail()
                if orgs:
                    org = orgs[0]
                    ctepOid = JobControl.getCtepId(docId)
        if nameTitle:
            result.append(u"""\
  <resp_party%s>
   <name_title>%s</name_title>
""" % (ctepPid and (u" ctep-id='%s'" % ctepPid) or u'', escape(nameTitle)))
            if org:
                result.append(u"""\
   <organization%s>%s</organization>
""" % (ctepOid and (u" ctep-id='%s'" % ctepOid) or u'', escape(org)))
            if phone:
                result.append(u"""\
   <phone>%s</phone>
""" % escape(phone))
            if email:
                result.append(u"""\
   <email>%s</email>
""" % escape(email))
            result.append(u"""\
  </resp_party>
""")
        result = u"".join(result)
        return result

class CTEPID(PostProcess):
    """
    Plugs in real value for ctep-id attribute if appropriate.
    """

    __pattern = re.compile(CTEP_ID)

    @classmethod
    def getPattern(cls):
        return cls.__pattern

    @staticmethod
    def convert(match):
        ctepId = JobControl.getCtepId(match.group(1))
        return ctepId and escape(ctepId) or u""

class NCTTrialID(PostProcess):
    """
    Plugs in NCT ID for trial.
    """

    __pattern = re.compile(NCTTRIALID)

    @classmethod
    def getPattern(cls):
        return cls.__pattern

    @staticmethod
    def convert(match):
        dom = NCTTrialID.cdrDom
        for node in dom.getElementsByTagName('OtherID'):
            idType = idString = u""
            for child in node.childNodes:
                if child.nodeName == 'IDType':
                    idType = cdr.getTextContent(child)
                elif child.nodeName == 'IDString':
                    idString = cdr.getTextContent(child)
            if idString and idType == 'ClinicalTrials.gov ID':
                return escape(idString)
        return u""

class CTEPTrialID(PostProcess):
    """
    Plugs in CTEP ID for trial.
    """

    __pattern = re.compile(CTEPTRIALID)

    @classmethod
    def getPattern(cls):
        return cls.__pattern

    @staticmethod
    def convert(match):
        dom = CTEPTrialID.cdrDom
        for node in dom.getElementsByTagName('OtherID'):
            idType = idString = u""
            for child in node.childNodes:
                if child.nodeName == 'IDType':
                    idType = cdr.getTextContent(child)
                elif child.nodeName == 'IDString':
                    idString = cdr.getTextContent(child)
            if idString and idType == 'CTEP ID':
                return escape(idString)
        return u""

class DCPTrialID(PostProcess):
    """
    Plugs in DCP ID for trial.
    """

    __pattern = re.compile(DCPTRIALID)

    @classmethod
    def getPattern(cls):
        return cls.__pattern

    @staticmethod
    def convert(match):
        dom = DCPTrialID.cdrDom
        for node in dom.getElementsByTagName('OtherID'):
            idType = idString = u""
            for child in node.childNodes:
                if child.nodeName == 'IDType':
                    idType = cdr.getTextContent(child)
                elif child.nodeName == 'IDString':
                    idString = cdr.getTextContent(child)
            if idString and idType == 'DCP ID':
                return escape(idString)
        return u""

class Trial:
    """
    Object to carry processing information about a single trial.
    Public members include:

        cdrId
            Integer for CDR document's primary key.

        docVersion
            Integer for version of document used to produce the exported
            trial information.

        getCdrDoc()
            Returns the DOM tree for the repository's original CDR
            document from which the vendor output was generated.
            We return this on the fly rather than carrying it as
            a member of the Trial object in order to avoid chewing
            up too much memory at run time.
    """

    def __init__(self, cdrId, docVer):
        self.cdrId            = cdrId
        self.docVersion       = docVer

    def getCdrDoc(self):
        return JobControl.getCdrDoc(self.cdrId, self.docVersion)

class JobControl:
    """
    Master object which handles export processing.  Public members
    include:

        createExportDirectory()
            Figures out where to store the output and creates the
            location.

        collectProtocols()
            Creates a list of trials to be exported.

        processProtocols()
            Filters each trial document, applies all of the post-
            processing routines which have been registered in the
            program, determines whether we need to send the trial
            to NLM (either because it is a new trial, or because
            it is a trial which has changed since we last exported
            it, or because it has been published again after having
            been dropped), and if so, writes the clinical_trial
            document in the export directory.

        createArchive()
            Packs up the set of trial documents (and the list of
            dropped trials if any) in a compressed archive to be
            made available for retrieval by NLM.

        extractIntId(idString)
            Class method for extracting the integer portion of
            a string (or None if there are no digit characters
            in the argument).

        getVendorDoc(docId)
            Retrieves the document XML from the pub_proc_cg table
            and returns the DOM tree for the parsed document.
            Implemented as a class method in order to use the
            JobControl's database cursor.

        getCdrDoc(docId, docVersion)
            Retrieves the document XML from the repository for the
            specified version of a CDR document (or the current
            working version if no version is specified).  Implemented
            as a class method in order to use the JobControl's
            database cursor.
    """

    __nonDigitsPattern = re.compile(NON_DIGITS)
    __statusPattern    = re.compile(STATUS)
    __verifPattern     = re.compile(VERIFICATION_DATE)
    __conn             = cdrdb.connect()
    __cursor           = __conn.cursor()

    def __init__(self, argv):
        self.__jobTime    = time.localtime(time.time())
        self.__logName    = os.path.join(cdr.DEFAULT_LOGDIR, 'CTRPExport.log')
        self.__debugging  = False
        self.__verbose    = False
        self.__maxDocs    = sys.maxint
        self.__baseDir    = OUTPUTBASE
        self.__dirName    = time.strftime("%Y%m%d%H%M%S", self.__jobTime)
        self.__failed     = []
        self.__trials     = []
        self.__exported   = []
        self.__suppress   = {}
        self.__nctIds     = {}
        self.__parseArgs(argv)
        self.__processes  = PostProcess.getDerivedClasses()

    def createExportDirectory(self):
        self.__outputDir = os.path.join(self.__baseDir, self.__dirName)
        os.makedirs(self.__outputDir)
        self.__logName  = os.path.join(self.__outputDir, LOGNAME)
        self.__logWrite("created output directory %s" % self.__outputDir)
        if self.__debugging:
            self.__debugDir = os.path.join(self.__outputDir, 'debug')
            os.makedirs(self.__debugDir)
        for process in self.__processes:
            self.__logWrite("using post-process %s" % process)

    def collectProtocols(self):

        #--------------------------------------------------------------
        # Find trials in spreadsheet which are published as InScopeProtocols.
        #--------------------------------------------------------------
        book = ExcelReader.Workbook('d:/Inetpub/wwwroot/report4896.xls')
        trials = {}
        for i in range(2):
            sheet = book[i]
            for row in sheet:
                try:
                    docId = int(row[0].val)
                except:
                    continue
                self.__cursor.execute("""\
                    SELECT d.doc_version, t.name
                      FROM pub_proc_doc d
                      JOIN pub_proc_cg c
                        ON c.pub_proc = d.pub_proc
                       AND c.id = d.doc_id
                      JOIN doc_version v
                        ON d.doc_version = v.num
                       AND v.id = d.doc_id
                      JOIN doc_type t
                        ON t.id = v.doc_type
                     WHERE d.doc_id = ?""", docId, timeout=300)
                rows = self.__cursor.fetchall()
                if rows:
                    docVersion, docType = rows[0]
                    if docType == 'InScopeProtocol':
                        trials[docId] = Trial(docId, docVersion)
                    else:
                        self.__logWrite("doc type for CDR%d is %s" %
                                        (docId, docType))
                else:
                    self.__logWrite("CDR%d not published" % docId)

        #--------------------------------------------------------------
        # Remember the list of trials to be exported.
        #--------------------------------------------------------------
        docIds = trials.keys()
        docIds.sort()
        for docId in docIds:
            self.__trials.append(trials[docId])
        self.__logWrite("selected %d candidate trials for export" %
                        len(self.__trials))

    def processProtocols(self):
        self.__cursor.execute("""\
            CREATE TABLE #exported
                     (id INT,
                     xml NTEXT,
                  status VARCHAR(255))""")
        self.__conn.commit()
        nDocs = len(self.__trials)
        i = 0
        total = min(nDocs, self.__maxDocs)
        while i < total:
            doc = self.__trials[i]
            self.__logWrite("processing CDR%d" % doc.cdrId)
            if not self.__canSkip(doc):
                try:
                    docXml = self.__filterDoc(doc)
                    if docXml:
                        docXml = self.__postProcessDoc(doc, docXml)
                        if self.__needsExport(doc, docXml):
                            self.__saveDoc(doc, docXml)
                except Exception, e:
                    msg = "failure processing CDR%d: %s" % (doc.cdrId, e)
                    self.__logWrite(msg)
                    self.__failed.append(doc)
            i += 1
            if self.__debugging or self.__verbose:
                sys.stderr.write("\rprocessed %d of %d documents" % (i, total))
        self.__logWrite("done processing %d protocol documents" % i)

    def createArchive(self):
        if os.path.isdir(self.__outputDir):
            collName = "%s/%s" % (self.__dirName, COLLECTION_NAME)
            tarName  = "%s/%s" % (self.__dirName, TARNAME)
            os.chdir(self.__baseDir)
            exportFile = open(collName, 'wb')
            exportFile.write("""\
<?xml version='1.0' encoding='utf-8'?>
<study_collection>
""")
            for trial in self.__exported:
                fileName = "CDR%d.xml" % trial.cdrId
                pathName = os.path.join(self.__dirName, fileName)
                f = open(pathName, "rb")
                xmlDoc = f.read()
                f.close()
                exportFile.write(xmlDoc)
            exportFile.write("""\
</study_collection>
""")
            exportFile.close()
            files = collName
            outFile = os.popen('%s cjf %s %s 2>&1' % (TARCMD, tarName, files))
            output  = outFile.read()
            result  = outFile.close()
            if result:
                self.__logWrite("tar return code: %d" % result)
            if output:
                self.__logWrite(output)
            self.__logWrite("%s created" % tarName)

    @classmethod
    def extractIntId(cls, idString):
        try:
            return int(cls.__nonDigitsPattern.sub('', idString))
        except:
            return None

    @classmethod
    def getVendorDoc(cls, docId):
        if type(docId) in (str, unicode):
            docId = cls.extractIntId(docId)
        query = "SELECT xml FROM pub_proc_cg WHERE id = ?"
        cls.__cursor.execute(query, docId, timeout = 300)
        rows = cls.__cursor.fetchall()
        if not rows:
            raise Exception("Unable to find vendor output for %d" % docId)
        return xml.dom.minidom.parseString(rows[0][0].encode('utf-8'))

    @classmethod
    def getCdrDoc(cls, docId, docVersion = None):
        if type(docId) in (str, unicode):
            docId = cls.extractIntId(docId)
        if docVersion:
            cls.__cursor.execute("""\
                SELECT xml
                  FROM doc_version
                 WHERE id = ?
                   AND num = ?""", (docId, docVersion), timeout = 300)
        else:
            cls.__cursor.execute("SELECT xml FROM document WHERE id = ?",
                                 docId, timeout = 300)
        rows = cls.__cursor.fetchall()
        if not rows:
            ver = docVersion and ("version %d" % docVersion) or "CWD"
            raise Exception("Unable to find %s for CDR%d\n", (ver, docId))
        docXml = rows[0][0].encode('utf-8')
        name = "d:/tmp/CDR%d-%d.xml" % (docId, docVersion or 0)
        return xml.dom.minidom.parseString(docXml)

    @classmethod
    def lookupOspaMenuItem(cls, docId):
        """
        Looks for an OSPA MenuItem in a term document, along with a
        display name (which is optional according to the schema, but
        should always be present for OSPA menu items).  Returns a
        tuple whose first value is a flag indicating whether the
        menu item was found and whose second value is the value of
        the display name if present (or None).
        """
        if type(docId) in (str, unicode):
            docId = cls.extractIntId(docId)
        cls.__cursor.execute("""\
            SELECT d.value
              FROM query_term t
   LEFT OUTER JOIN query_term d
                ON d.doc_id = t.doc_id
               AND d.path = '/Term/MenuInformation/MenuItem/DisplayName'
               AND LEFT(d.node_loc, 8) = LEFT(t.node_loc, 8)
             WHERE t.doc_id = ?
               AND t.path = '/Term/MenuInformation/MenuItem/MenuType'
               AND t.value = 'Key cancer type'""", docId, timeout = 300)
        rows = cls.__cursor.fetchall()
        return rows and (True, rows[0][0]) or (False, None)

    def __parseArgs(self, argv):
        self.__argv = argv
        try:
            longopts = ["optimize", "debugging",
                        "verbose", "basedir=", "maxtestdocs=", "since=",
                        "force=", "force-list="]
            opts, args = getopt.getopt(argv[1:], "odvs:b:m:f:F:", longopts)
        except getopt.GetoptError, e:
            self.__usage()
        for o, a in opts:
            if o in ("-d", "--debugging"):
                self.__debugging = True
                self.__logWrite("running with DEBUGGING on")
            elif o in ("-v", "--verbose"):
                self.__verbose = True
                self.__logWrite("running with VERBOSE on")
            elif o in ("-b", "--basedir"):
                self.__baseDir = a
                self.__logWrite("using base directory %s" % a)
            elif o in ("-m", "--maxtestdocs"):
                try:
                    self.__maxDocs = int(a)
                    self.__logWrite("max docs set to %d" % self.__maxDocs)
                except:
                    self.__usage()
            else:
                self.__usage()
        if args:
            self.__usage()

    @classmethod
    def getCtepId(cls, cdrId):
        intId = cdr.exNormalize(cdrId)[1]
        cls.__cursor.execute("""\
            SELECT t.name
              FROM doc_type t
              JOIN document d
                ON d.doc_type = t.id
             WHERE d.id = ?""", intId)
        rows = cls.__cursor.fetchall()
        if not rows:
            return None
        if rows[0][0] == 'Person':
            usage = 'CTSU_Person_ID'
        elif rows[0][0] == 'Organization':
            usage = 'CTEP_Institution_Code'
        else:
            return None
        cls.__cursor.execute("""\
            SELECT m.value
              FROM external_map m
              JOIN external_map_usage u
                ON u.id = m.usage
             WHERE u.name = ?
               AND m.doc_id = ?""", (usage, intId))
        rows = cls.__cursor.fetchall()
        return rows and rows[0][0] or None

    def __usage(self):
        sys.stderr.write("""\
usage: %s [options]

options:
    -d                  turn on debugging
    -v                  show progress
    -b P                create new output directory as child of base path P
    -m N                maximum number of docs to process (for testing)
    --debugging         turn on debugging
    --verbose           show progress
    --basedir=P         create new output directory as child of base path P
    --maxtestdocs=N     maximum number of docs to process (for testing)
    --usage             print this message

  * Default base directory for output is %s
    
""" % (self.__argv[0], OUTPUTBASE))
        sys.exit(1)

    def __filterDoc(self, trial):
        self.__cursor.execute("SELECT xml FROM pub_proc_cg WHERE id = ?",
                              trial.cdrId, timeout = 300)
        docXml = self.__cursor.fetchall()[0][0].encode('utf-8')
        if self.__debugging:
            n = os.path.join(self.__debugDir, "%d-vendor.xml" % trial.cdrId)
            self.__saveFile(n, docXml)
        self.__cursor.execute("""\
            SELECT value
              FROM query_term
             WHERE doc_id = ?
               AND path = '/InScopeProtocol/CTGovOwnershipTransferInfo'
                        + '/CTGovOwnerOrganization'""", trial.cdrId,
                              timeout = 300)
        transferringOwnership = self.__cursor.fetchall() and "Yes" or "No"
        parms = [['transferringOwnership', transferringOwnership]]
        filt = ['set:CTRP Export Set']
        result = cdr.filterDoc('guest', filt, doc = docXml, parm = parms)
        if type(result) in (str, unicode):
            self.__logWrite("failure filtering CDR%d: %s" % (trial.cdrId,
                                                               result))
            self.__failed.append(trial)
            return ""
        filteredXml, warnings = result
        if warnings:
            self.__logWrite("filtering CDR%d: %s" % (trial.cdrId, warnings))
        if not JobControl.__hasVerificationDate(result[0]):
            self.__logWrite("CDR%d missing required verification date" %
                            trial.cdrId)
            self.__failed.append(trial)
            return ""
        return filteredXml

    def __postProcessDoc(self, trial, docXml):
        cdrDom = trial.getCdrDoc()
        i = 0
        while i < len(self.__processes):
            if type(docXml) == str:
                docXml = unicode(docXml, 'utf-8')
            postProcess = self.__processes[i]
            if self.__debugging:
                self.__logWrite("post-processing class %s" % postProcess)
                name = "CDR-%d-%d.xml" % (trial.cdrId, i)
                path = os.path.join(self.__debugDir, name)
                self.__saveFile(path, docXml.encode('utf-8'))
            postProcess.setTrial(trial, cdrDom)
            docXml = postProcess.getPattern().sub(postProcess.convert, docXml)
            i += 1
            for warning in postProcess.getWarnings():
                self.__logWrite(warning)
        return docXml

    @classmethod
    def __lookupStatus(cls, docXml):
        match = cls.__statusPattern.search(docXml)
        if not match:
            return ''
        return match.group(1)

    @classmethod
    def __hasVerificationDate(cls, docXml):
        match = cls.__verifPattern.search(docXml)
        return match and True or False

    def __canSkip(self, trial):
        """
        Determines whether we can skip this trial because we can
        safely say no changes have occurred in it.  Always false
        for the CTRP version of this program.
        """
        return False

    def __needsExport(self, trial, newXml):
        """
        Determines whether a given trial should be sent to NLM by
        comparing the newly created document for the trial with
        the document we last sent to NLM for the trial.
        Always true for the CTRP version of the program.
        """
        return True
        
    def __saveDoc(self, trial, docXml):
        trial.newStatus = JobControl.__lookupStatus(docXml)
        filePath = os.path.join(self.__outputDir, "CDR%d.xml" % trial.cdrId)
        if type(docXml) == unicode:
            xmlBytes = docXml.encode('utf-8')
        else:
            xmlBytes = docXml
            docXml = unicode(xmlBytes, 'utf-8')
        self.__saveFile(filePath, xmlBytes)
        self.__exported.append(trial)

    def __saveFile(self, where, what):
            f = file(where, 'wb')
            f.write(what)
            f.close()

    def __lookupNctId(self, cdrId):
        if cdrId in self.__nctIds:
            return self.__nctIds[cdrId]
        self.__cursor.execute("""\
            SELECT i.value
              FROM query_term i
              JOIN query_term t
                ON i.doc_id = t.doc_id
               AND LEFT(i.node_loc, 8) = LEFT(t.node_loc, 8)
             WHERE i.path  = '/InScopeProtocol/ProtocolIDs/OtherID/IDString'
               AND t.path  = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
               AND t.value = 'ClinicalTrials.gov ID'
               AND i.doc_id = ?""", cdrId, timeout = 300)
        rows = self.__cursor.fetchall()
        nctId = rows and rows[0][0] or None
        self.__nctIds[cdrId] = nctId
        return nctId

    def __logWrite(self, what):
        cdr.logwrite(what, self.__logName)

#----------------------------------------------------------------------
# Processing entry point.
#
# Program logic summary:
#
# 1. Collect invocation settings.
# 2. Create export directory in file system.
# 3. Gather list of protocols to be processed.
# 4. For each protocol document (skipping suppressed trials)
#    a. Retrieve vendor XML for document from pub_proc_cg.
#    b. Filter document XML using XSL/T.
#    c. Post-process results of filtering.
#    d. Compare processed XML with xml column in pub_proc_nlm.
#    e. If differences found, write processed XML to export directory.
# 5. Pack up the trials for export.
#
#----------------------------------------------------------------------

def main():
    jc = JobControl(sys.argv)
    jc.createExportDirectory()
    jc.collectProtocols()
    jc.processProtocols()
    jc.createArchive()

if __name__ == '__main__':
    main()
