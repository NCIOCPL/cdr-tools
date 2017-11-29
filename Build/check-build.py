#!/usr/bin/env python

"""
Compare a CDR build package with the live file system.

Note that there are separate utilities in the DevTools directory
for comparing Filters and Schemas against the live repository.

OCECDR-4300
"""

import argparse
import os
import re
import subprocess
import sys

class Control:
    """
    Master driver with runtime configuration settings for processing.

    Class values:
      SCRIPTS - directory where the build scripts are stored
      EXCLUDES - location of file identifying things we don't check
      SKIP - directories we don't check with this tool
      POPEN_OPTS - options for launching a sub process

    Attributes:
      drive - letter representing the disk volume for the CDR
      opts - runtime control settings
    """

    SCRIPTS = os.path.split(os.path.abspath(sys.argv[0]))[0]
    EXCLUDES = os.path.join(SCRIPTS, "diff.excludes").replace("\\", "/")
    SKIP = "Schemas", "Emailers"
    POPEN_OPTS = dict(
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    def __init__(self):
        """
        Collect and validate runtime settings.
        """

        self.drive = self.find_cdr_drive()
        self.opts = self.fetch_options()

    def run(self):
        """
        Compare all the directories.

        We only do a single iteration of the outer loop, because
        we empty out the `dirs` sequence, which leaves the `walk()`
        method nothing to recurse with.

        Start by building up the arguments for the diff invocations,
        adding two None placeholders for the source and target dirs.
        """

        args = ["diff", "-r"]
        if not self.opts.all:
            args += ["-X", self.EXCLUDES]
        if self.opts.brief:
            args.append("-q")
        if self.opts.ignore_space_change:
            args.append("-b")
        if self.opts.ignore_all_space:
            args.append("-w")
        if self.opts.ignore_case:
            args.append("-i")
        if self.opts.unified:
            args.append("-u")
        if self.opts.context:
            args.append("-c")
        args += [None, None]
        for path, dirs, files in os.walk(self.opts.build):
            while dirs:
                directory = dirs.pop(0)
                source = os.path.join(path, directory)
                if directory in self.SKIP:
                    continue
                elif directory == 'Inetpub':
                    target = self.drive + ":/Inetpub"
                else:
                    target = self.drive + ":/cdr/" + directory
                args[-2:] = source.replace("\\", "/"), target
                p = subprocess.Popen(args, **self.POPEN_OPTS)
                output, errout = p.communicate()
                if errout:
                    raise Exception(errout)
                sys.stdout.write(self.filtered(output))

    def filtered(self, output):
        """
        Prepare the diff output for display.

        Don't clutter up the output yakking about all the dross in the
        DEV web root (unless the user has asked for everything).
        """

        if self.opts.all:
            return output
        pattern = r"only in d:[\\/]inetpub[\\/]wwwroot: [^\n]*\n"
        output = re.sub(pattern, "", output, flags=re.IGNORECASE)
        return output

    def fetch_options(self):
        """
        Parse and validate the command-line arguments.
        """

        desc = "Compare the CDR live file system to a new CDR release set"
        parser = argparse.ArgumentParser(description=desc)
        parser.add_argument("build", help="location of build files")
        parser.add_argument("--brief", "-q", action="store_true",
                            help="only report which files differ")
        parser.add_argument("--ignore-case", "-i", action="store_true",
                            help="ignore case differences in file contents")
        parser.add_argument("--ignore-space-change", "-b", action="store_true",
                            help="ignore changes in the amount of white space")
        parser.add_argument("--ignore-all-space", "-w", action="store_true",
                            help="ignore all white space")
        parser.add_argument("--all", "-a", action="store_true",
                            help="also report expected differences")
        parser.add_argument("--reverse", "-r", action="store_true",
                            help="put new release set on left side of diff")
        group = parser.add_mutually_exclusive_group()
        group.add_argument("--context", "-c", action="store_true",
                           help="output three lines of context on each side")
        group.add_argument("--unified", "-u", action="store_true",
                           help="generate a unified context diff")
        return parser.parse_args()

    @staticmethod
    def find_cdr_drive():
        """
        Find out which drive has the CDR installation.
        """

        for drive in "DCEFGH":
            if os.path.isdir("{}:/cdr".format(drive)):
                return drive
        return None

if __name__ == "__main__":
    "Top-level entry point."
    Control().run()
