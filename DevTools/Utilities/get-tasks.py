import argparse
import datetime
import json
import pickle
import pytz
import cdrdb

class Job:
    def __init__(self, job_id, next_run_time, job_state):
        self.job_id = job_id
        self.next_run_time = next_run_time
        self.job_state = pickle.loads(job_state)
        self.name = self.job_state.get("name")
        self.args = self.job_state.get("args") or ["None", "None", "None"]
        self.trigger = Trigger(self.job_state.get("trigger"))
    def __cmp__(self, other):
        return cmp((self.name, self.args), (other.name, other.args))
    def print_raw(self):
        print repr(self.job_state)
    def print_short(self):

        print self.name
        print json.dumps(self.args[2:])
        print self.trigger
        if not self.next_run_time:
            print "Disabled"
        print
    def print_full(self):
        print "=" * 70
        print "%10s: %s" % ("Job ID", self.job_id)
        print "%10s: %s" % ("Job Name", self.name)
        print "%10s: %s" % ("Enabled?", self.next_run_time and "Yes" or "No")
        print "%10s: %s" % ("Class", self.args[0])
        print "%10s: %s" % ("Task", self.args[2])
        print "%10s: %s" % ("Options", self.args[3])
        print "%10s: %s" % ("Trigger", self.job_state.get("trigger"))

class Trigger:
    def __init__(self, trigger):
        self.fields = {}
        for field in trigger.fields:
            self.fields[field.name] = str(field)
    def __str__(self):
        names = ("minute", "hour", "day", "month", "day_of_week")
        values = [self.fields.get(name, "*") for name in names]
        return "   ".join(values)

parser = argparse.ArgumentParser()
parser.add_argument("--raw", action="store_true")
parser.add_argument("--short", action="store_true")
opts = parser.parse_args()
fields = "id", "next_run_time", "job_state"
query = cdrdb.Query("scheduler_jobs", *fields)
for job in sorted([Job(*row) for row in query.execute().fetchall()]):
    if opts.raw:
        job.print_raw()
    elif opts.short:
        job.print_short()
    else:
        job.print_full()
