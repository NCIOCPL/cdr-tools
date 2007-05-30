import cdr, cdrdb, ModifyDocs, re, sys, ExcelReader

class Date:
    def __init__(self,dateStr):
        splitDate = dateStr.split('-')
        self.year = int(splitDate[0])
        self.month = int(splitDate[1])
        self.day = int(splitDate[2])

class DocAndDate:
    def __init__(self, id, date):
        self.id = id
        self.dt = date
        self.dtCls = Date(date)

DocsAndDates = {}
class ParsedExcelFile:
    def __init__(self, fileName): 
        firstRow = True
        book = ExcelReader.Workbook(fileName)
        sheet = book[0]
        for row in sheet.rows:
            if firstRow:
                firstRow = False
            else:
                id = row.cells[0].val
                date = row.cells[2]
                formattedDate = str(date)
                dtTmp = Date(formattedDate)
                # if year is over 2050, subtract 100 to make it in 1900's
                if dtTmp.year >= 2050: 
                    formattedDate="%s-%s-%s" % (dtTmp.year-100,dtTmp.month,dtTmp.day)
                # if year is before 1950, ignore. Must be an error
                if dtTmp.year > 1950:
                    intid = int(id)
                    DocsAndDates[intid] = DocAndDate(intid,formattedDate)
    

excelFile = ParsedExcelFile('D:\home\kidderc\entry-dates.xls')

#----------------------------------------------------------------------
# The Filter class is given to the ModifyDocs.Job object, which invokes
# the getDocIds() method to retrieve a list of CDR document IDs for
# processing.
#----------------------------------------------------------------------
class FilterFor3160:
    def getDocIds(self):
        sIn = " and doc_id in ("
        for id in DocsAndDates:
            sIn += "%d," % id

        sIn = sIn[:-1]
        sIn += ")"
            
        conn = cdrdb.connect('CdrGuest')
        cursor = conn.cursor()
        query = """\
select doc_id from query_term
where path = '/InScopeProtocol/ProtocolSources/ProtocolSource/DateReceived'
and value = '2002-06-22' %s """ % sIn
        cursor.execute(query)
        
        return [row[0] for row in cursor.fetchall()]


#----------------------------------------------------------------------
# The Transform class is given to the ModifyDocs.Job object, which in
# turn gives it to each ModifyDocs.Doc object.  The run() method of
# this class takes a cdr.Doc object and returns a (possibly) modified
# copy of that object's xml member.
#----------------------------------------------------------------------
class TransformFor3160:
    def __init__(self):
        pass # self.pattern = re.compile("TermName")
    def run(self, docObj):
        sId = docObj.id[3:] # remove CDR
        doc_id = int(sId) # convert to int
        docAndDate = DocsAndDates[doc_id]
        sDate = "%d-%02d-%02d" % (docAndDate.dtCls.year,docAndDate.dtCls.monthdocAndDate.dtCls.month,docAndDate.dtCls.day)
        filter = """\
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

 <!-- Update the date with what's in the Spreadsheet -->
 <xsl:template                  match = 'ProtocolSources/ProtocolSource/DateReceived'>
      <DateReceived>%s</DateReceived>
 </xsl:template>
</xsl:transform>
""" % sDate
        response = cdr.filterDoc('guest', filter, doc = docObj.xml, inline = 1)
        if type(response) in (type(""), type(u"")):
            raise Exception("Failure in normalizeDoc: %s" % response)
        return response[0]
    

# main portion of script
job = ModifyDocs.Job("ckidder", "charlie123", FilterFor3160(), TransformFor3160(),
                     "Update DateReceived element (3160)",
                    testMode=True)
job.run()

