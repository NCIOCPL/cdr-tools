import cdr, sys, os
session = cdr.login('rmk','***REDACTED***')
err = cdr.checkErr(session)
if err:
    print "failure logging in: " % err
    sys.exit(1)
for schema in sys.argv[1:]:
    print "schema: %s" % schema
    try:
        schemaDoc = open(schema).read()
    except:
        print "\t... can't open schema"
        continue
    query = "CdrCtl/Title = '%s' and CdrCtl/DocType = 'schema'" % schema
    results = cdr.search(session, query)
    if len(results) < 1:
        print "\t... schema not found in CDR"
    else:
        for result in results:
            print "comparing document %s" % result.docId
            doc = cdr.getDoc(session, result.docId, getObject = 1)
            if type(doc) == type(""):
                print "getDoc(%s): %s" % (result.docId, doc)
            else:
                filename = "%s.tmp" % result.docId
                try:
                    open(filename, "w").write(doc.xml)
                except:
                    print "\t... failure writing %s" % filename
                    continue
                diff = os.popen('diff -b %s %s' % (filename, schema)).read()
                print diff
cdr.logout(session)
