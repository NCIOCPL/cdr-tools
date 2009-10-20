#----------------------------------------------------------------------
#
# $Id$
#
# Creates and saves a serialized copy of the lookup table values for
# the emailer server.
#
#----------------------------------------------------------------------

try:

    import cdr, cdrdb, time, pickle, EmailerProtSites, bz2, cdrmailcommon

    start  = time.time()
    tables = []
    conn   = cdrdb.connect('CdrGuest')
    cursor = conn.cursor()

    #----------------------------------------------------------------------
    # Load up the rows for the country lookup table.
    #----------------------------------------------------------------------
    cursor.execute("""\
        SELECT doc_id, value
          FROM query_term
         WHERE path = '/Country/CountryFullName'
      ORDER BY value""")
    tables.append(('emailer_country', cursor.fetchall()))

    #----------------------------------------------------------------------
    # Load up the rows for the state lookup table.
    #----------------------------------------------------------------------
    cursor.execute("""\
        SELECT n.doc_id, n.value, c.int_val
          FROM query_term n
          JOIN query_term c
            ON n.doc_id = c.doc_id
         WHERE c.path = '/PoliticalSubUnit/Country/@cdr:ref'
           AND n.path = '/PoliticalSubUnit/PoliticalSubUnitFullName'
      ORDER BY n.value""")
    tables.append(('emailer_state', cursor.fetchall()))

    #----------------------------------------------------------------------
    # Load up the rows for the personal name suffix lookup table.
    #----------------------------------------------------------------------
    dtInfo = cdr.getDoctype('guest', 'Person')
    for vvList in dtInfo.vvLists:
        if vvList[0] == 'StandardProfessionalSuffix':
            tables.append(('emailer_suffix', [[col] for col in vvList[1]]))

    #----------------------------------------------------------------------
    # Load up the rows for the protocol site picklist table.
    #----------------------------------------------------------------------
    tables.append(EmailerProtSites.load())

    #----------------------------------------------------------------------
    # Upload the new values.
    #----------------------------------------------------------------------
    bytes   = pickle.dumps(tables)
    bytes   = bz2.compress(bytes)
    conn    = cdrmailcommon.emailerConn('dropbox')
    cursor  = conn.cursor()
    cursor.execute("""\
        INSERT INTO lookup_values (pickle, uploaded)
             VALUES (%s, NOW())""", bytes)
    conn.commit()
    elapsed = time.time() - start
    print "elapsed: %f" % elapsed
    cdr.logwrite("uploaded emailer lookup values; processing time %f seconds" %
                 elapsed)

except Exception, e:
    import cdr
    cdr.logwrite(str(e), tback = True)
