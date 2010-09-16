/*
 * $Id$
 *
 * Please manually convert the following InScope trials into CTGov trials.
 * In all cases, we attempted to convert them through the normal process
 * but they failed to be converted.
 * 
 * 1. Force conversion of CDR524078 (NCT00388960)
 *    (Duplicate - CDR517382 - (NCT00388960) will remain blocked.)
 * 2. Force conversion of CDR562439 (NCT00378794)
 *    (Duplicate - CDR511856 (NCT00378794) will remain blocked.)
 * 3. Force conversion of CDR491241 (NCT00346255).
 *    (Duplicate - CDR683236 (NCT00346255) will be blocked when conversion is
 *    completed.)
 *
 * BZIssue::4910
 */

USE cdr
DECLARE @new_comment VARCHAR(80)
SET @new_comment = 'rmk 2010-09-16: manually rerouted import at '
                 + 'William''s request (BZIssue::4910)'

UPDATE ctgov_import
   SET cdr_id = 524078,
       disposition = 5,
       dt = GETDATE(),
       comment = CASE
                     WHEN comment IS NULL THEN @new_comment
                     ELSE CAST(comment AS VARCHAR(100)) + '; ' + @new_comment
                 END
  WHERE nlm_id = 'NCT00388960'

UPDATE ctgov_import
   SET cdr_id = 562439,
       disposition = 5,
       dt = GETDATE(),
       comment = CASE
                     WHEN comment IS NULL THEN @new_comment
                     ELSE CAST(comment AS VARCHAR(100)) + '; ' + @new_comment
                 END
 WHERE nlm_id = 'NCT00378794'

UPDATE ctgov_import
   SET cdr_id = 491241,
       disposition = 5,
       dt = GETDATE(),
       comment = CASE
                     WHEN comment IS NULL THEN @new_comment
                     ELSE CAST(comment AS VARCHAR(100)) + '; ' + @new_comment
                 END
 WHERE nlm_id = 'NCT00346255'

GO
