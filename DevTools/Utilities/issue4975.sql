/*
 * $Id$
 * BZIssue::4975
 */
SELECT * from ctgov_import where nlm_id in ('NCT00513227', 'NCT00389571', 'NCT00678223', 'NCT00078546', 'NCT00488592', 'NCT00629109', 'NCT00041158')
select nlm_id, disposition, cdr_id, dropped, force, downloaded from ctgov_import where nlm_id in ('NCT00678769', 'NCT00507767', 'NCT00297895', 'NCT00678223', 'NCT00608257', 'NCT00499772', 'NCT00955019', 'NCT00037817')
select * from ctgov_disposition

/*
Records to be manually updated in the ctgov_import table:

1. CDR ID: 559148 
current NCT ID : NCT00513227 is now obsolete.
New NCT ID: NCT00507767 

Direct all updates from NCT00507767 to CDR 559148.
**NCT00507767 is marked as a duplicate**

UPDATE ctgov_import SET cdr_id = 559148, disposition = 5 WHERE nlm_id = 'NCT00507767'

2. CDR 472034 
current NCT ID: NCT00389571 is now obsolete.
new NCT ID: NCT00297895 
Direct all updates from NCT00297895 to CDR 472034.
**NCT00297895 is marked as a duplicate**

UPDATE ctgov_import SET cdr_id = 472034, disposition = 5 WHERE nlm_id = 'NCT00297895'

3. CDR 595388 
current NCT ID: NCT00678223 is now obsolete.
new NCT ID: NCT00678223 
Direct all updates from NCT00678223  to CDR 595388 

**NCT00678769 is marked as a duplicate**

-- SEE CHANGED INSTRUCTIONS BELOW

4. CDR 360874
current NCT ID: NCT00078546 is obsolete.
new NCT ID: NCT00608257
Direct all updates from NCT00608257 to  CDR 360874

INSERT INTO ctgov_import (nlm_id, disposition, dt, force, cdr_id) VALUES ('NCT00608257', 5, GETDATE(), 'Y', 360874)

5. CDR 558028
current NCT ID: NCT00499772
new NCT ID: NCT00499772
Direct all updates from NCT00499772 to CDR 558028

**NCT00488592 is marked as duplicate**

UPDATE ctgov_import SET cdr_id = 558028, disposition = 5, force = 'Y', dropped = 'N' WHERE nlm_id = 'NCT00499772'

6. CDR 583208
current NCT ID: NCT00629109 is obsolete
new NCT ID: NCT00955019
Direct updates from NCT00955019 to CDR 583208

INSERT INTO ctgov_import (nlm_id, disposition, dt, force, cdr_id) VALUES ('NCT00955019', 5, GETDATE(), 'Y', 583208)

7. CDR 69448
current NCT ID: NCT00041158
new NCT ID: NCT00037817
Direct updates from NCT00037817 to CDR 69448

**NCT00037817 is marked as a duplicate.**

UPDATE ctgov_import SET cdr_id = 69448, disposition = 5 WHERE nlm_id = 'NCT00037817'

-- Bob, comment #1:
Looks like some of these have been dropped by NLM:

NCT00678223
NCT00499772
NCT00955019

-- William, comment #2:
That is correct for:
> NCT00499772
> NCT00955019
They are both completed on the NLM web site. The above two trials have Active
statuses in the CDR. If we do a force download, would their statuses update?

However, the new ID for NCT00678223  is NCT00678769
Please direct all updates from NNCT00678769 to CDR595388.

UPDATE ctgov_import SET cdr_id = 595388, disposition = 5 WHERE nlm_id = 'NCT00678769'

*/
