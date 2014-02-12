import ExcelReader, cdrdb, lxml.etree as etree, sys, re, cgi

fp = open("exceptions.log", "w")
def getTitles(cursor, sheet, source):
    count = 0
    for row in sheet:
        try:
            title = None
            cdrId = int(row[0].val)
            cursor.execute("SELECT xml FROM document WHERE id = ?", cdrId)
            tree = etree.XML(cursor.fetchall()[0][0].encode('utf-8'))
            for node in tree.findall('ProtocolTitle'):
                if node.get('Type').lower().strip() == 'original':
                    title = cgi.escape(re.sub("\\s+", ' ',
                                              node.text.strip().encode('utf-8')))
            print """\
 <trial>
  <cdr_id>%d</cdr_id>
  <%s_id>%s</%s_id>
  <nct_id>%s</nct_id>
  <original_title>%s</original_title>
  <current_status>%s</current_status>
 </trial>""" % (cdrId, source, fix(row[1]), source, fix(row[2]), title,
                fix(row[3]))
            count += 1
        except Exception, e:
            fp.write("exception: %s\n" % e)
    sys.stderr.write("found titles for %d %s trials\n" % (count, source))

def fix(me):
    if not me:
        return ''
    return cgi.escape(me.val.strip().encode('utf-8'))

cursor = cdrdb.connect('CdrGuest').cursor()
book = ExcelReader.Workbook('d:/Inetpub/wwwroot/report4896.xls')
print "<trials>"
getTitles(cursor, book[0], "CTEP")
getTitles(cursor, book[1], "DCP")
print "</trials>"
fp.close()
