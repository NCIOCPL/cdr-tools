#----------------------------------------------------------------------
#
# $Id$
#
# Populate Country documents with ISO short names and alpha-2 codes.
#
# BZIssue::1626
#
#----------------------------------------------------------------------
import cdr, cdrdb, sys, ModifyDocs, xml.dom.minidom

#----------------------------------------------------------------------
# The Filter class is given to the ModifyDocs.Job object, which invokes
# the getDocIds() method to retrieve a list of CDR document IDs for
# processing.
#----------------------------------------------------------------------
class Filter:
    def __init__(self, countries):
        self.countries = countries
    def getDocIds(self):
        return self.countries.keys()

#----------------------------------------------------------------------
# The Transform class is given to the ModifyDocs.Job object, which in
# turn gives it to each ModifyDocs.Doc object.  The run() method of
# this class takes a cdr.Doc object and returns a (possibly) modified
# copy of that object's xml member.
#
# See comment at top for this job's logic.
#----------------------------------------------------------------------
class Transform:
    def __init__(self, countries):
        self.countries = countries
    def run(self, docObj):
        docIds = cdr.exNormalize(docObj.id)
        country = self.countries[docIds[1]]
        code = country.code
        name = (country.name.replace('&', '&amp;')
                            .replace('"', '&quot;')
                            .replace("'", '&apos;'))
        filter = (u"""\
<?xml version='1.0' encoding='UTF-8'?>

<xsl:transform                version = '1.0' 
                            xmlns:xsl = 'http://www.w3.org/1999/XSL/Transform'
                            xmlns:cdr = 'cips.nci.nih.gov/cdr'>

 <xsl:output                   method = 'xml'/>

 <!--
 =======================================================================
 Copy most things straight through.
 ======================================================================= -->
 <xsl:template                  match = '@*|node()|comment()|
                                         processing-instruction()'>
  <xsl:copy>
   <xsl:apply-templates        select = '@*|node()|comment()|
                                         processing-instruction()'/>
  </xsl:copy>
 </xsl:template>

 <!-- Modify ProtocolDesign elements. -->
 <xsl:template                  match = 'PostalCodePosition'>
  <xsl:copy>
   <xsl:apply-templates        select = '@*|node()|comment()|
                                         processing-instruction()'/>
  </xsl:copy>
  <xsl:element                   name = 'ISOShortCountryName'>
   <xsl:value-of               select = '"%s"'/>
  </xsl:element>
  <xsl:element                   name = 'ISOAlpha2CountryCode'>
   <xsl:value-of               select = '"%s"'/>
  </xsl:element>
 </xsl:template>
</xsl:transform>
""" % (name, code)).encode('utf-8')
        if docObj.xml.find('<PostalCodePosition') == -1:
            job.log("%s: missing PostalCodePosition element")
            return docObj.xml
        result = cdr.filterDoc('guest', filter, doc = docObj.xml, inline = 1)
        if type(result) in (type(""), type(u"")):
            message = "%s: %s" % (docObj.id, result)
            if type(message) is unicode:
                message = message.encode('utf-8')
            job.log(message)
            sys.stderr.write("%s\n" % message)
            return docObj.xml
        return result[0]

if len(sys.argv) < 3:
    sys.stderr.write("usage: %s uid pwd [LIVE]\n" % sys.argv[0])
    sys.exit(1)
testMode = len(sys.argv) < 4 or sys.argv[3] != "LIVE"

#----------------------------------------------------------------------
# Map CDR country names to ISO short country names (all others are
# exact matches, disregarding case).
#----------------------------------------------------------------------
nameMap = {
    "Czechoslovakia": "CZECH REPUBLIC",
    "Democratic People's Republic of Korea":
        "KOREA, DEMOCRATIC PEOPLE'S REPUBLIC OF",
    # "Federated Republic of Yugoslavia": "SERBIA AND MONTENEGRO",
    "Iran": "IRAN, ISLAMIC REPUBLIC OF",
    "Kingdom of Bahrain": "BAHRAIN",
    "Macedonia": "MACEDONIA, THE FORMER YUGOSLAV REPUBLIC OF",
    "People's Republic of Bangladesh": "BANGLADESH",
    "Republic of Bulgaria": "BULGARIA",
    "Republic of Georgia": "GEORGIA",
    "Republic of Korea": "KOREA, REPUBLIC OF",
    "Republic of Marshall Islands": "MARSHALL ISLANDS",
    "Republic of San Marino": "SAN MARINO",
    "Republic of Singapore": "SINGAPORE",
    "Republic of South Africa": "SOUTH AFRICA",
    "Russia": "RUSSIAN FEDERATION",
    # "Serbia": "SERBIA AND MONTENEGRO",
    "Socialist Republic of Viet Nam": "VIET NAM",
    "Sultanate of Oman": "OMAN",
    # "Tanganyika": "TANZANIA",
    "Union of Myanmar": "MYANMAR",
    "United Republic of Tanzania": "TANZANIA, UNITED REPUBLIC OF",
    "United States of America": "UNITED STATES",
    # "Virgin Islands": "VIRGIN ISLANDS, U.S.",
}

#----------------------------------------------------------------------
# Objects to hold CDR doc ID, ISO short country name, and ISO alpha-2 code.
# For unmapped countries, the name is the CDR full name, and the code is
# None.
#----------------------------------------------------------------------
class Country:
    def __init__(self, docId, isoName, isoCode = None):
        self.docId = docId
        self.name  = isoName
        self.code  = isoCode

#----------------------------------------------------------------------
# Returns a tuple of matched and unmatched countries.
#----------------------------------------------------------------------
def collectCountries():
    isoCountries = {}
    cdrCountries = {}
    unmatched    = []
    dom = xml.dom.minidom.parse('iso_3166-1_list_en.xml')
    for node in dom.documentElement.childNodes:
        if node.nodeName == 'ISO_3166-1_Entry':
            name = None
            code = None
            for child in node.childNodes:
                if child.nodeName == 'ISO_3166-1_Country_name':
                    name = cdr.getTextContent(child)
                elif child.nodeName == 'ISO_3166-1_Alpha-2_Code_element':
                    code = cdr.getTextContent(child)
            if name and code:
                isoCountries[name] = code

    conn = cdrdb.connect('CdrGuest')
    cursor = conn.cursor()
    cursor.execute("""\
        SELECT doc_id, value
          FROM query_term
         WHERE path = '/Country/CountryFullName'""")
    for docId, name in cursor.fetchall():
        if name in nameMap:
            isoName = nameMap[name]
        else:
            isoName = name.upper()
        if isoName in isoCountries:
            cdrCountries[docId] = Country(docId, isoName,
                                          isoCountries[isoName])
        else:
            unmatched.append(Country(docId, name))
    return (cdrCountries, unmatched)

mappedCountries, unmappedCountries = collectCountries()
job = ModifyDocs.Job(sys.argv[1], sys.argv[2], Filter(mappedCountries),
                     Transform(mappedCountries),
                     "Adding ISO country names and codes (request #1626).",
                     testMode = testMode)
for country in unmappedCountries:
    job.log("CDR%d (%s) not mapped" % (country.docId,
                                       country.name.encode('utf-8')))
job.run()
