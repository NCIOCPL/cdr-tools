#----------------------------------------------------------------------
#
# $Id$
#
# "Is there a way to programmatically populate and  map the CTGov Mapping
# table with all the organization and person IDs  which are in InScopeProtocol
# documents? When the InScopeProtocol documents are converted to become
# CTGovProtocol documents, all the organizations and persons that are not in
# the CTGov mapping table are left unlinked in the protocol documents, as
# expected.  Users spend a lot of time going through the documents to
# determine which ones have not been linked in order to link them and map
# them.  Since all the organizations and persons are already in the CDR
# (for all transferred trials), if there is a way to populate the mapping
# table programmatically before the transfers take place, this will save us
# a lot of time."
#
# BZIssue::4725 (see comments #3 and #10 for refinements of the requirements)
#
#----------------------------------------------------------------------
import cdr, lxml.etree as etree, re, sys, cdrdb

LOGFILE = "%s/Request4725.log" % cdr.DEFAULT_LOGDIR
AGENCIES = "CT.gov Agencies"
OFFICIALS = "CT.gov Officials"
INVESTIGATORS = "CT.gov Investigators"
FACILITIES = "CT.gov Facilities"
FILTERS = ['name:Set InScopeProtocol Status to Active',
           'set:Vendor InScopeProtocol Set']
countries = set()

class MappingControl:
    def __init__(self, cursor):
        self.mappings = { 'agencies': {}, 'officials': {}, 'investigators': {},
                          'facilities': {} }
        self.ambiguous = {}
        self.activePersons = self.findActiveDocs('Person', cursor)
        self.activeOrgs = self.findActiveDocs('Organization', cursor)
        cdr.logwrite("loaded %d active persons" % len(self.activePersons),
                     LOGFILE)
        cdr.logwrite("loaded %d active orgs" % len(self.activeOrgs), LOGFILE)
    @staticmethod
    def findActiveDocs(docType, cursor):
        cursor.execute("""\
            SELECT DISTINCT s.doc_id
                       FROM query_term s
                       JOIN active_doc a
                         ON a.id = s.doc_id
                      WHERE s.path = '/%s/Status/CurrentStatus'
                        AND s.value = 'Active'""" % docType)
        return set([row[0] for row in cursor.fetchall()])
    def addMapping(self, usage, value, docId):
        if usage not in self.mappings:
            raise Exception("unrecognized usage '%s'" % usage)
        mappings = self.mappings[usage]
        key = value.upper()
        if key not in mappings:
            mappings[key] = docId
        elif mappings[key] != docId:
            msg = "%s has two mappings: %s and %s" % (key, mappings[key], docId)
            cdr.logwrite(msg, LOGFILE)

class PersonalName:
    def __init__(self, node):
        self.first = self.middle = self.last = u""
        self.suffixes = []
        for child in node:
            if child.tag == 'GivenName':
                self.first = extractText(child)
            elif child.tag == 'MiddleInitial':
                self.middle = extractText(child)
            elif child.tag == 'SurName':
                self.last = extractText(child)
            elif child.tag == 'ProfessionalSuffix':
                self.suffixes.append(extractText(child))
    def makeKey(self):
        return u"%s|%s|%s" % (self.first, self.middle, self.last)
    def makeGarbledKey(self):
        name = u"%s %s" % (self.first, self.middle)
        name = u"%s %s" % (name.strip(), self.last)
        name = [name.strip()] + self.suffixes
        return u"||" + u", ".join(name)

class PostalAddress:
    countryMap = {
        u'KINGDOM OF BAHRAIN': u'Bahrain',
        u'U.S.A.': u'United States',
        u'REPUBLIC OF GEORGIA': u'Georgia',
        u"PEOPLE'S REPUBLIC OF BANGLADESH": u'Bangladesh',
        u'UNION OF MYANMAR': u'Myanmar',
        u'REPUBLIC OF SINGAPORE': u'Singapore',
        u'SULTANATE OF OMAN': u'Oman',
        u'UNITED REPUBLIC OF TANZANIA': u'Tanzania',
        u'REPUBLIC OF KOREA': u'Korea, Republic of',
        u'IRAN': u'Iran, Islamic Republic of',
        u'REPUBLIC OF SOUTH AFRICA': u'South Africa',
        u'MACEDONIA': u'Macedonia, The Former Yugoslav Republic of',
        u'FEDERATED REPUBLIC OF YUGOSLAVIA': u'Former Yugoslavia',
        u'SOCIALIST REPUBLIC OF VIET NAM': u'Vietnam',
        u'RUSSIA': u'Russian Federation',
        u'TAIWAN, PROVINCE OF CHINA': u'Taiwan',
        u'REPUBLIC OF MOLDOVA': u'Moldova, Republic of',
        u'REPUBLIC OF BULGARIA': u'Bulgaria'
    }
    def __init__(self, node = None):
        self.city = self.state = self.zip = self.country = u""
        if node is not None:
            for child in node:
                if child.tag == 'City':
                    self.city = extractText(child)
                elif child.tag == 'PoliticalSubUnitName':
                    self.state = extractText(child)
                elif child.tag == 'PostalCode_ZIP':
                    self.zip = extractText(child)
                elif child.tag == 'CountryName':
                    self.country = extractText(child)
                    countries.add(self.country)
    def makeKey(self):
        country = self.country
        if country.upper() in self.countryMap:
            country = self.countryMap[country.upper()]
        return u"%s|%s|%s|%s" % (self.city, self.state, self.zip, country)

def extractDocId(node):
    value = node.get('ref')
    if type(value) in (str, unicode):
        try:
            return cdr.exNormalize(value)[1]
        except:
            return None
    return None

def extractText(node):
    if node.text is None:
        return u""
    value = node.text.strip()
    return re.sub(u"\\s+", u' ', value)

def addAgencyMapping(node, control):
    docId = extractDocId(node)
    if docId not in control.activeOrgs:
        return
    value = extractText(node)
    control.addMapping('agencies', value, docId)

def addOfficialMapping(node, control):
    docId = extractDocId(node)
    if docId not in control.activePersons:
        return
    name = None
    affiliation = u""
    for child in node.findall('PersonNameInformation'):
        name = PersonalName(child)
    for child in node.findall('Contact/ContactDetail/OrganizationName'):
        affiliation = extractText(child)
    if name:
        key = u"%s|%s" % (name.makeKey(), affiliation)
        control.addMapping('officials', key, docId)
        key = u"%s|%s" % (name.makeGarbledKey(), affiliation)
        control.addMapping('officials', key, docId)

def addSiteMappings(node, control):
    siteName = u""
    for child in node.findall('SiteName'):
        siteName = extractText(child)
    if siteName and node.get('sitetype') == 'Organization':
        addFacilityMapping(node, siteName, control)
    for child in node.findall('ProtPerson'):
        addInvestigatorMapping(child, siteName, control)

def addInvestigatorMapping(node, siteName, control):
    name = None
    docId = extractDocId(node)
    if docId not in control.activePersons:
        return
    for child in node.findall('PersonNameInformation'):
        name = PersonalName(child)
    if name:
        key = u"%s|%s" % (siteName, name.makeKey())
        control.addMapping('investigators', key, docId)
        key = u"%s|%s" % (siteName, name.makeGarbledKey())
        control.addMapping('investigators', key, docId)

def addFacilityMapping(node, siteName, control):
    docId = extractDocId(node)
    if docId not in control.activeOrgs:
        return
    address = PostalAddress()
    for child in node.findall('ProtPerson/Contact/ContactDetail/PostalAddress'):
        address = PostalAddress(child)
        break
    key = u"%s|%s" % (siteName, address.makeKey())
    control.addMapping('facilities', key, docId)
        
def loadMappings(docId, docVer, control):
    response = cdr.filterDoc('guest', FILTERS, docId, docVer=docVer)
    if type(response) in (str, unicode):
        raise Exception(response)
    cdrTree = etree.XML(response[0])
    for node in cdrTree.findall('ProtocolAdminInfo/ProtocolLeadOrg'):
        for child in node.findall('LeadOrgName'):
            addAgencyMapping(child, control)
        for child in node.findall('LeadOrgPersonnel/ProtPerson'):
            addOfficialMapping(child, control)
    for node in cdrTree.findall('ProtocolAdminInfo/ProtocolSites/ProtocolSite'):
        addSiteMappings(node, control)

def collectMappings():
    cursor = cdrdb.connect("CdrGuest").cursor()
    cursor.execute("""\
        SELECT v.id, MAX(v.num)
          FROM doc_version v
          JOIN doc_type t
            ON t.id = v.doc_type
         WHERE t.name = 'InScopeProtocol'
      GROUP BY v.id
      ORDER BY v.id DESC""")
    rows = cursor.fetchall()
    cdr.logwrite("found %d protocols to process" % len(rows), LOGFILE)
    done = 0
    control = MappingControl(cursor)
    for docId, docVer in rows:
        try:
            loadMappings(docId, docVer, control)
        except Exception, e:
            cdr.logwrite("failure processing version %d of CDR%d: %s" %
                         (docVer, docId, e), LOGFILE)
        done += 1
        sys.stderr.write("\rprocessed %d of %d documents" % (done, len(rows)))
    mappingCount = 0
    for key in control.mappings:
        fp = open('d:/tmp/%s-mappings.txt' % key, 'w')
        values = control.mappings[key].keys()
        values.sort()
        cdr.logwrite("collected %d %s mappings" % (len(values), key), LOGFILE)
        for value in values:
            mappingCount += 1
            fp.write("%s\t%d\n" % (value.encode('utf-8'),
                                   control.mappings[key][value]))
        fp.close()
    cdr.logwrite("collected %d mappings from %d protocols" %
                 (mappingCount, done), LOGFILE)
    fp = open('d:/tmp/countries.txt', 'w')
    countryList = list(countries)
    countryList.sort()
    for country in countryList:
        try:
            fp.write("%s\n" % country.encode('utf-8'))
        except Exception, e:
            cdr.logwrite("Failure writing country: %s" % repr(e), LOGFILE)
            f = open('d:/tmp/country-set.txt', 'w')
            f.write(repr(countries))
            f.close()
    fp.close()

def populateMapping(value, docId, usageId, cursor):
    docId = int(docId)
    uValue = unicode(value, 'utf-8')
    cursor.execute("""\
        SELECT id, doc_id
          FROM external_map
         WHERE usage = ?
           AND value = ?""", (usageId, uValue))
    rows = cursor.fetchall()
    if rows:
        mappedId = rows[0][1]
        if mappedId is None:
            cursor.execute("""\
                UPDATE external_map
                   SET doc_id = ?,
                       usr = 2,
                       last_mod = GETDATE(),
                       bogus = 'N',
                       mappable = 'Y'
                 WHERE id = ?""", (docId, rows[0][0]))
            cdr.logwrite("updated '%s' (usage %d) to %d" %
                         (value, usageId, docId), LOGFILE)
        elif mappedId != docId:
            cdr.logwrite("unable to map '%s' (usage %d) to %d: "
                         "already mapped to %d" %
                         (value, usageId, docId, mappedId), LOGFILE)
        else:
            cdr.logwrite("value '%s' (usage %d) already mapped to %d" %
                         (value, usageId, docId), LOGFILE)
    else:
        cursor.execute("""\
            INSERT INTO external_map (usage, value, doc_id, usr, last_mod)
                 VALUES (?, ?, ?, 2, GETDATE())""",
                       (usageId, uValue, docId))
        cdr.logwrite("mapped '%s' (usage %d) to %d" % (value, usageId, docId),
                     LOGFILE)

def populateMappings():
    conn = cdrdb.connect()
    conn.setAutoCommit()
    cursor = conn.cursor()
    for usage in (AGENCIES, OFFICIALS, INVESTIGATORS, FACILITIES):
        cursor.execute("SELECT id FROM external_map_usage WHERE name = ?",
                       usage)
        usageId = cursor.fetchall()[0][0]
        suffix = usage.split()[-1].lower()
        fp = open('d:/tmp/%s-mappings.txt' % suffix)
        for line in fp:
            line = line.strip()
            try:
                value, docId = line.split('\t')
                populateMapping(value, docId, usageId, cursor)
            except Exception, e:
                cdr.logwrite("failure processing %s: %s" % (line, e), LOGFILE)
        fp.close()

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ('collect', 'populate'):
        sys.stderr.write("usage: Request4725.py collect|populate\n")
        sys.exit(2)
    if sys.argv[1] == 'collect':
        collectMappings()
    else:
        populateMappings()

if __name__ == '__main__':
    main()
