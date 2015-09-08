#----------------------------------------------------------------------
# $Id$
#
# Report of CTRP import statistics and problems. Run weekly for
# Christine. Keep the generated reports under version control so
# they will always be available for parsing (they're needed for
# error history).
#
# JIRA::OCECTS-132
#----------------------------------------------------------------------
import cdr
import cdrdb
import datetime
import glob
import lxml.etree as etree
import os
import re
import sys
import time
import urllib2
import xlrd
import xlwt
import zipfile

#----------------------------------------------------------------------
# Tracks all the known validation errors of a given class, where the
# classes are CTRP data problems ("ctrp") or CIAT data problems ("ciat").
# The latter are typically the result of the window of time during which
# a new trial has not yet been given PDQ indexing by CIAT. These errors
# are stored in two files in the current working directory, under the
# names "ctrp_errors" and "ciat_errors" with each error stored on a
# separate line in the Python repr() format. The files must be updated
# to incorporate new errors encountered by future report runs. When
# you do that, it is very important that you modify the logic of the
# Trial.validate() method to map the validation error string to the
# value which will be used in the report to represent the error (for
# CTRP data problems) or to add logging for CIAT data errors which
# aren't the result of new trials waiting for PDQ indexing (for example,
# violation of linking rules).
#----------------------------------------------------------------------
class Errors:
    def __init__(self, error_type):
        fp = open("%s_errors" % error_type)
        self.values = set([eval(line.strip().lower()) for line in fp])
        fp.close()
    def __contains__(self, what):
        return what in self.values

#----------------------------------------------------------------------
# Represents the import, validation, and publication status for a
# single CTRP clinical trial document. More information is collected
# for "open" trials, as they are the ones which are published to the
# cancer.gov web site.
#----------------------------------------------------------------------
class Trial:
    NOT_PUSHED = "Not pushed to Cancer.gov - "
    OPEN_STATUSES = set(["recruiting", "available", "not yet recruiting",
                         "enrolling by invitation", "suspended",
                         "temporarily not available"])
    CLOSED_STATUSES = set(["approved for marketing", "completed",
                           "terminated", "withdrawn",
                           "active, not recruiting"])
    NO_MATCH = "no match found in content model for type ctgovprotocol"
    def __init__(self, bytes, filename, report):
        self.filename = filename
        self.import_date = None
        self.pub_version_date = None
        self.ctrp_data_publishable = False
        self.last_publication_job = None
        self.publication_failure = None
        self.publication_messages = None
        self.publication_removal = None
        self.verification_date = None
        self.nct_id = self.status = self.open = self.cdr_id = None
        self.ctrp_errors = set()
        root = etree.XML(bytes)
        for node in root.findall("id_info/nct_id"):
            try:
                self.nct_id = node.text.upper().strip()
            except:
                pass
        for node in root.findall("overall_status"):
            try:
                self.status = node.text.strip()
            except:
                pass
        if self.status:
            self.open = self.status.lower() in Trial.OPEN_STATUSES
        if self.open:
            for node in root.findall("verification_date"):
                self.verification_date = node.text
            self.cdr_id = self.get_cdr_id()
            self.import_date = self.get_import_date(report)
            self.pub_version_date = self.get_pub_version_date()
            if self.import_date and self.pub_version_date:
                if self.pub_version_date >= self.import_date:
                    self.ctrp_data_publishable = True
            if self.ctrp_data_publishable:
                self.check_publication_status()
            else:
                self.validate()
    def __cmp__(self, other):
        return cmp(self.nct_id, other.nct_id)
    def get_cdr_id(self):
        if not self.nct_id:
            return None
        Report.cursor.execute("""\
SELECT cdr_id
  FROM ctgov_import
 WHERE nlm_id = ?""", self.nct_id)
        rows = Report.cursor.fetchall()
        return rows and rows[0][0] or None
    def get_import_date(self, report):
        if self.cdr_id:
            Report.cursor.execute("""\
SELECT MAX(dt)
  FROM audit_trail
 WHERE document = ?
   AND dt > '2015-06-12' /* switch from NLM to CTRP trials */
   AND dt < '%s 23:59:59'
   AND program = 'cdrPutDoc'
   AND comment LIKE 'ImportCTGovProtocols: %%'""" % report.iso_date,
                                  self.cdr_id)
            rows = Report.cursor.fetchall()
            if rows:
                return rows[0][0]
        return None
    def get_pub_version_date(self):
        if not self.cdr_id:
            return None
        Report.cursor.execute("""\
SELECT MAX(dt)
  FROM doc_version
 WHERE id = ?
   AND publishable = 'Y'""", self.cdr_id)
        rows = Report.cursor.fetchall()
        return rows and rows[0][0] or None
    def check_publication_status(self):
        Report.cursor.execute("""\
SELECT MAX(p.id)
  FROM pub_proc p
  JOIN pub_proc_doc d
    ON d.pub_proc = p.id
 WHERE d.doc_id = ?
   AND p.status = 'Success'""", self.cdr_id)
        rows = Report.cursor.fetchall()
        if rows and rows[0][0]:
            self.last_publication_job = rows[0][0]
            Report.cursor.execute("""\
SELECT failure, messages, removed
  FROM pub_proc_doc
 WHERE doc_id = ?
   AND pub_proc = ?""", (self.cdr_id, self.last_publication_job))
            rows = Report.cursor.fetchall()
            self.publication_failure = rows[0][0] == "Y"
            self.publication_messages = rows[0][1]
            self.publication_removal = rows[0][2] == "Y"

            # So far, we've only seen one DTD validation error in
            # exported trial documents whose CDR counterparts passed
            # schema validation (missing required Gender element).
            # If any additional problems appear, this code will need
            # to be modified to map the DTD validation's message to
            # an error string to be used in the report. The report
            # will abort if it sees an unrecognized validation message.
            # 2015-08-04: Skip over anomalous XSL/T failure.
            if self.publication_failure and self.publication_messages:
                elig_error = "Eligibility content does not follow the DTD"
                msg = self.publication_messages.lower()
                if ("xslt error" in msg and "denormalizeterm" in msg and
                    "attribute 'encoding'" in msg):
                    return
                if elig_error in self.publication_messages:
                    if msg.count("gender") == 1:
                        self.ctrp_errors.add("missing gender")
                        return
                sys.stderr.write("\n")
                Report.fail("unrecognized publication failure %s" %
                            repr(self.publication_messages))

    #------------------------------------------------------------------
    # Run CDR schema and link validation on the version of the CDR
    # document created by the most recent import. It's possible that
    # some of the validation errors will have been fixed in subsequent
    # versions, but we're reporting on the validity of what we got
    # from CTRP. The processing of validation errors found depends on
    # the recognition of known error messages, stored in the current
    # working directory (see the Errors class above). If we come across
    # an error message we haven't seen before, the report will abort
    # and the new message will need to be stored in one of the two
    # error message files, and the code below may need to be modified
    # to map the new message to a report error string, or (in the case
    # of errors CIAT should correct), log the message.
    #
    # Had to wrap the call to cdr.valDoc in a looped try block,
    # because the network sometimes gets unhappy with too many sockets
    # being opened as quickly as we're doing it.
    #
    # Modified 2015-06-30 to perform the validation on the current
    # working copy of the document, because it turns out that the
    # import script doesn't always create a new version.
    #------------------------------------------------------------------
    def validate(self):
        tries = 3
        while tries > 0:
            try:
                response = cdr.valDoc(Report.session, "CTGovProtocol",
                                      self.cdr_id)
                break
            except Exception, e:
                sys.stderr.write("\n")
                Report.log("validation CDR%d: %e" % (self.cdr_id, e))
                tries -= 1
                Report.log("%d more tries" % tries)
                if tries < 1:
                    Report.fail("exiting; report possible network failure")
                time.sleep(1)
        errors = cdr.getErrors(response, asSequence=True, errorsExpected=False)
        for error in errors:
            normalized_error = error.lower()
            if normalized_error in Report.ciat_errors:
                if normalized_error.startswith("failed link target rule"):
                    sys.stderr.write("\n")
                    Report.log("CDR%d: %s" % (self.cdr_id, repr(error)))
            elif (Trial.NO_MATCH in normalized_error and
                  not self.verification_date):
                self.ctrp_errors.add("missing verification_date")
            elif normalized_error not in Report.ctrp_errors:
                msg = "CDR%d: don't recognize %s" % (self.cdr_id, repr(error))
                sys.stderr.write("\n")
                Report.fail(msg)
            elif "private use characters" not in normalized_error:
                msg = "CDR%d: unrecognized %s" % (self.cdr_id, repr(error))
                sys.stderr.write("\n")
                Report.fail(msg)
            else:
                # XXX adjust code if you add to ctrp_errors file!!!
                self.ctrp_errors.add("private use characters")

    class FileNameAnomaly:
        def __init__(self, nct_id, status):
            self.nct_id = nct_id
            self.status = status
        def __cmp__(self, other):
            return cmp(self.nct_id, other.nct_id)
    def check_for_file_name_anomaly(self):
        if not self.nct_id:
            error = ("File name is \"%s\"; NCT ID in document empty" %
                     self.filename)
            return Trial.FileNameAnomaly("None", error)
        if self.filename.upper()[:-4] != self.nct_id.upper():
            return Trial.FileNameAnomaly(self.nct_id,
                                         "File name is \"%s\"" % self.filename)
        return None

#----------------------------------------------------------------------
# Remember the first time we saw each particular error for each trial
# document. We collect this information by parsing all of the previous
# reports.
#----------------------------------------------------------------------
class History:
    def get(self, key, default=None):
        return self.errors.get(key, default)
    def __init__(self):
        self.errors = {}
        for name in glob.glob("%s/ctrp-trial-report*.xls" % Report.DIR):
            book = xlrd.open_workbook(name)
            sheet = book.sheet_by_name("Invalid Documents")
            for row_number in range(1, sheet.nrows):
                nct_id = sheet.cell(row_number, 0).value
                error = sheet.cell(row_number, 2).value
                start_date = sheet.cell(row_number, 3).value
                start_date = xlrd.xldate_as_tuple(start_date, book.datemode)
                start_date = datetime.date(*start_date[:3])
                key = (nct_id.upper(), error.lower())
                if key in self.errors:
                    if start_date < self.errors[key]:
                        self.errors[key] = start_date
                else:
                    self.errors[key] = start_date
            try:
                sheet = book.sheet_by_name("File Name Anomalies")
            except:
                continue
            for row_number in range(1, sheet.nrows):
                nct_id = sheet.cell(row_number, 0).value
                error = sheet.cell(row_number, 1).value
                start_date = sheet.cell(row_number, 2).value
                start_date = xlrd.xldate_as_tuple(start_date, book.datemode)
                start_date = datetime.date(*start_date[:3])
                key = (nct_id.upper(), error.lower())
                if key in self.errors:
                    if start_date < self.errors[key]:
                        self.errors[key] = start_date
                else:
                    self.errors[key] = start_date

#----------------------------------------------------------------------
# Collect information for each of the clinical trial documents in a
# CTRP set for a particular day and generate an Excel workbook containing
# summary information about the disposition of the documents and any
# problems detected. See https://tracker.nci.nih.gov/browse/OCECTS-132
# for details.
#----------------------------------------------------------------------
class Report:
    LOGFILE = cdr.DEFAULT_LOGDIR + "/weekly-ctrp-report.log"
    DIR = "weekly-ctrp-reports"
    URL_BASE = "https://trials.nci.nih.gov/pa/pdqgetFileByDate.action"
    FILENAME_BASE = "CTRP-TO-CANCER-GOV-EXPORT"
    session = "guest"
    cursor = cdrdb.connect("CdrGuest").cursor()
    ciat_errors = Errors("ciat")
    ctrp_errors = Errors("ctrp")
    def __init__(self):
        self.start = time.time()
        self.file_name_anomalies = []
        if len(sys.argv) < 2:
            Report.fail("usage: %s date|filename" % sys.argv[0])
        if sys.argv[1].lower().endswith(".zip"):
            self.filename = sys.argv[1]
            match = re.match("%s-(.*).zip" % Report.FILENAME_BASE,
                             self.filename, re.I)
            if not match:
                Report.fail("%s doesn't match pattern %s-YYYY-MM-DD.zip" %
                            (self.filename, Report.FILENAME_BASE))
            self.iso_date = match.group(1)
            Report.log("reporting from existing trial set %s" % self.filename)
        else:
            self.iso_date = sys.argv[1]
            self.filename = "%s-%s.zip" % (Report.FILENAME_BASE, self.iso_date)
            url = "%s?date=%s" % (Report.URL_BASE, self.filename)
            Report.log("fetching %s" % url)
            try:
                server = urllib2.urlopen(url)
                doc = server.read()
                code = server.code
                if code == 200:
                    fp = open(self.filename, "wb")
                    fp.write(doc)
                    fp.close()
                else:
                    Report.fail("%s: HTTP code %s" % (url, code))
            except Exception, e:
                Report.fail("Fetching %s: %s\n" % (url, e))
        if not zipfile.is_zipfile(self.filename):
            Report.fail("%s is not a zipfile" % repr(self.filename))
        match = re.match(r"(\d\d\d\d)-(\d\d)-(\d\d)", self.iso_date)
        if not match:
            Report.fail("%s is not a well-formed ISO date" %
                        repr(self.iso_date))
        self.import_date = datetime.date(int(match.group(1)),
                                         int(match.group(2)),
                                         int(match.group(3)))
        Report.log("import date is %s" % self.import_date)
        Report.cursor.execute("""\
SELECT processed
  FROM ctrp_trial_set
 WHERE filename = ?""", self.filename)
        rows = Report.cursor.fetchall()
        if not rows:
            Report.fail("can't find trial set for %s in database" %
                        repr(self.filename))
        Report.processed = rows[0][0]
        self.zipfile = zipfile.ZipFile(self.filename)
        self.bogus_trials = self.open_trials = self.closed_trials = 0
        self.published_successfully = 0
        self.trials_with_ctrp_errors = []
        self.trials_with_ciat_errors = []
        self.total_trials = len(self.zipfile.namelist())
        processed = 0
        for name in self.zipfile.namelist():
            trial = Trial(self.zipfile.read(name), name, self)
            anomaly = trial.check_for_file_name_anomaly()
            if anomaly:
                self.file_name_anomalies.append(anomaly)
            if not trial.nct_id:
                self.bogus_trials += 1
            elif trial.open:
                self.open_trials += 1
                if trial.ctrp_data_publishable:
                    if trial.ctrp_errors:
                        self.trials_with_ctrp_errors.append(trial)
                    else:
                        self.published_successfully += 1
                elif trial.ctrp_errors:
                    self.trials_with_ctrp_errors.append(trial)
                else:
                    self.trials_with_ciat_errors.append(trial)
            else:
                self.closed_trials += 1
            processed += 1
            sys.stderr.write("\rprocessed %d of %d trial documents" %
                             (processed, self.total_trials))
        sys.stderr.write("\n")
    def write(self):
        date = self.iso_date.replace("-", "")
        report_path = "%s/ctrp-trial-report-%s.xls" % (Report.DIR, date)
        try:
            os.delete(report_path)
        except:
            pass
        history = History()
        book = xlwt.Workbook(encoding="UTF-8")
        header_style = xlwt.easyxf("font: bold True;")
        section_style = xlwt.easyxf("font: bold True; align: horiz centre;")
        comma_style = xlwt.easyxf("", "#,###")
        date_style = xlwt.XFStyle()
        date_style.num_format_str = "yyyy-mm-dd"
        sheet = book.add_sheet("Summary")
        sheet.col(0).width = 5000
        sheet.col(1).width = 2000
        sheet.col(2).width = 7500
        title = "CTRP %s Clinical Trial Set" % self.iso_date
        row_num = 0
        sheet.write_merge(row_num, row_num, 0, 2, title, section_style)
        row_num += 1
        sheet.write(row_num, 0, "Total trials")
        sheet.write(row_num, 1, self.total_trials, comma_style)
        if self.bogus_trials:
            row_num += 1
            sheet.write(row_num, 0, "Failed import")
            sheet.write(row_num, 1, self.bogus_trials, comma_style)
            sheet.write(row_num, 2, "See \"File Name Anomalies\" sheet")
        row_num += 1
        sheet.write(row_num, 0, "\"Open\" trials")
        sheet.write(row_num, 1, self.open_trials, comma_style)
        row_num += 1
        sheet.write(row_num, 0, "\"Closed\" trials")
        sheet.write(row_num, 1, self.closed_trials, comma_style)
        row_num += 2
        sheet.write_merge(row_num, row_num, 0, 2, "\"Open\" Trial Breakdown",
                          section_style)
        row_num += 1
        sheet.write(row_num, 0, "Invalid")
        sheet.write(row_num, 1, len(self.trials_with_ctrp_errors), comma_style)
        sheet.write(row_num, 2, "See \"Invalid Documents\" sheet")
        row_num += 1
        sheet.write(row_num, 0, "Under review by CIAT")
        sheet.write(row_num, 1, len(self.trials_with_ciat_errors), comma_style)
        row_num += 1
        sheet.write(row_num, 0, "Pushed to GateKeeper")
        sheet.write(row_num, 1, self.published_successfully, comma_style)
        sheet = book.add_sheet("Invalid Documents")
        sheet.col(0).width = 4000
        sheet.col(1).width = 3500
        sheet.col(2).width = 12000
        sheet.col(3).width = 5000
        sheet.col(4).width = 5500
        sheet.write(0, 0, "NCT ID", header_style)
        sheet.write(0, 1, "CDR ID", header_style)
        sheet.write(0, 2, "Status", header_style)
        sheet.write(0, 3, "Date of First Failure", header_style)
        sheet.write(0, 4, "Date of Latest Failure", header_style)
        row_number = 1
        for trial in sorted(self.trials_with_ctrp_errors):
            for error in sorted(trial.ctrp_errors):
                error = Trial.NOT_PUSHED + error
                key = (trial.nct_id.upper(), error.lower())
                start_date = history.errors.get(key, self.import_date)
                cdr_id = "CDR%d" % trial.cdr_id
                sheet.write(row_number, 0, trial.nct_id)
                sheet.write(row_number, 1, cdr_id)
                sheet.write(row_number, 2, error)
                sheet.write(row_number, 3, start_date, date_style)
                sheet.write(row_number, 4, self.import_date, date_style)
                row_number += 1
        if self.file_name_anomalies:
            sheet = book.add_sheet("File Name Anomalies")
            sheet.col(0).width = 4000
            sheet.col(1).width = 12000
            sheet.col(2).width = 5000
            sheet.col(3).width = 5500
            sheet.write(0, 0, "NCT ID", header_style)
            sheet.write(0, 1, "Status", header_style)
            sheet.write(0, 2, "Date of First Failure", header_style)
            sheet.write(0, 3, "Date of Latest Failure", header_style)
            row_number = 1
            for anomaly in sorted(self.file_name_anomalies):
                key = (anomaly.nct_id.upper(), anomaly.status.lower())
                start_date = history.errors.get(key, self.import_date)
                sheet.write(row_number, 0, anomaly.nct_id)
                sheet.write(row_number, 1, anomaly.status)
                sheet.write(row_number, 2, start_date, date_style)
                sheet.write(row_number, 3, self.import_date, date_style)
                row_number += 1
        fp = open(report_path, "wb")
        book.save(fp)
        fp.close()
        ctrp_errors = len(self.trials_with_ctrp_errors)
        ciat_review = len(self.trials_with_ciat_errors)
        published = self.published_successfully
        elapsed = time.time() - self.start
        Report.log("saved %s" % report_path)
        Report.log("%d trial docs processed" % len(self.zipfile.namelist()))
        Report.log("%d document(s) have no NCT ID" % self.bogus_trials)
        Report.log("%d \"closed\" trials" % self.closed_trials)
        Report.log("%d \"open\" trials" % self.open_trials)
        Report.log("%d trials with CTRP errors" % ctrp_errors)
        Report.log("%d trials under CIAT review" % ciat_review)
        Report.log("%d trial documents published" % published)
        Report.log("report processing time: %f seconds" % elapsed)
    @classmethod
    def log(cls, what):
        sys.stderr.write(what + "\n")
        cdr.logwrite(what, cls.LOGFILE)
    @staticmethod
    def fail(why):
        Report.log("FAIL: %s" % why)
        sys.exit(1)

if __name__ == "__main__":
    report = Report()
    report.write()
