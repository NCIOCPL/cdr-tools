#!/usr/bin/env python
"""
Dump CDR scheduled tasks.

Run `python get-tasks.py --help` for usage information
"""

import argparse
import datetime
import json
import pickle
import pytz
import cdrdb

class Job:
    """Task managed from the CDR Scheduler

    Instance attributes:
      job_id - unique identifier for the task
      next_run_time - datetime object for next firing of task (if enabled)
      job_state - dictionary containing all information about the task
      name - display string for name of task
      args - tuple containing job class name, unique id, task class name,
             and options
      trigger - cron-like scheduling information for task
    """

    def __init__(self, job_id, next_run_time, job_state):
        """Extract the task information from the database columns.
        """

        self.job_id = job_id
        self.next_run_time = next_run_time
        self.job_state = pickle.loads(job_state)
        self.name = self.job_state.get("name")
        self.args = self.job_state.get("args") or ["None", "None", "None"]
        self.trigger = Trigger(self.job_state.get("trigger"))

    def __cmp__(self, other):
        """Sort the tasks on their display names.
        """

        return cmp((self.name, self.args), (other.name, other.args))

    def print_raw(self):
        """Print the python representation of the job_state dictionary.
        """

        print(repr(self.job_state))

    def print_short(self):
        """Show a brief display for the task.

        Prints display title, task class name, options, and schedule.
        Also indicates that the task is disable where appropriate.
        """

        print(self.name)
        print(json.dumps(self.args[2:]))
        print(self.trigger)
        if not self.next_run_time:
            print("Disabled")
        print()

    def print_full(self):
        """
        Display a more complete listing of the properties of the task.
        """

        print("=" * 70)
        print("%10s: %s" % ("Job ID", self.job_id))
        print("%10s: %s" % ("Job Name", self.name))
        print("%10s: %s" % ("Enabled?", self.next_run_time and "Yes" or "No"))
        print("%10s: %s" % ("Class", self.args[0]))
        print("%10s: %s" % ("Task", self.args[2]))
        print("%10s: %s" % ("Options", self.args[3]))
        print("%10s: %s" % ("Trigger", self.job_state.get("trigger")))

class Trigger:
    """
    Cron-like values controlling when the task is fired.

    Attributes:
      fields - dictionary of values for when the task runs
    """

    def __init__(self, trigger):
        """Extract fields from CronTrigger object.
        """

        self.fields = {}
        for field in trigger.fields:
            self.fields[field.name] = str(field)

    def __str__(self):
        """Show cron-like display of scheduling values.
        """

        names = ("minute", "hour", "day", "month", "day_of_week")
        values = [self.fields.get(name, "*") for name in names]
        return "   ".join(values)

def main():
    """
    Collect command-line options and dump the tasks as requested.
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--raw", action="store_true",
                        help="output Python code for values")
    parser.add_argument("-s", "--short", action="store_true",
                        help="show brief display of task information")
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

if __name__ == "__main__":
    """Allow loading of file as a module (e.g., by Python code checkers).
    """

    main()
