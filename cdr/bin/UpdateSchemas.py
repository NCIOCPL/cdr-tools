import cdr, sys, glob
if len(sys.argv) < 4:
    print "usage: DiffSchemas user-id password schema [schema ...]"
    sys.exit(1)
session = cdr.login(sys.argv[1], sys.argv[2])
err = cdr.checkErr(session)
if err:
    print "failure logging in: " % err
    sys.exit(1)
for token in sys.argv[3:]:
    for schema in glob.glob(token):
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
""" % (schema, open(schema).read())
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
