import cdr, sys
session = cdr.login('rmk','***REDACTED***')
err = cdr.checkErr(session)
if err:
    print "failure logging in: " % err
    sys.exit(1)
for schema in sys.argv[1:]:
    print "schema: %s" % schema
    query = "CdrCtl/Title = '%s' and CdrCtl/DocType = 'schema'" % schema
    results = cdr.search(session, query)
    if len(results) < 1:
        doc = """\
<CdrDoc Type='schema' Id=''>
 <CdrDocCtl>
  <DocTitle>%s</DocTitle>
 </CdrDocCtl>
 <CdrDocXml><![CDATA[%s]]></CdrDocXml>
</CdrDoc>
""" % (schema, open(schema.read()))
        id = cdr.addDoc(session, doc = doc, checkIn = 'Y', ver = 'Y')
        print "addDoc: " + id
    else:
        for result in results:
            doc = cdr.getDoc(session, result.docId, 'Y', getObject = 1)
            if type(doc) == type(""):
                print "getDoc(%s): %s" % (result.docId, doc)
            else:
                doc = """\
<CdrDoc Type='schema' Id='%s'>
 <CdrDocCtl>
  <DocTitle>%s</DocTitle>
 </CdrDocCtl>
 <CdrDocXml><![CDATA[%s]]></CdrDocXml>
</CdrDoc>
""" % (result.docId, schema, open(schema).read())
                id = cdr.repDoc(session, doc = doc, checkIn='Y', ver = 'Y')
                print "repDoc(%s): %s" % (result.docId, id)
cdr.logout(session)
