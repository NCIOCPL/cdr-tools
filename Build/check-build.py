#!/Python/python.exe

"""
Compare a CDR build package with the live file system.

"""

import argparse
import os
import subprocess
import sys

class Control:
    """
    Master driver with runtime configuration settings for processing.
    """

    PIPE = subprocess.PIPE
    STDOUT = subprocess.STDOUT
    POPEN_OPTS = dict(shell=True, stdout=PIPE, stderr=PIPE)
    SCRIPTS = os.path.split(os.path.abspath(sys.argv[0]))[0]
    EXCLUDES = os.path.join(SCRIPTS, "diff.excludes")
    SKIP = "Schemas", "Emailers"

    def __init__(self):
        """
        Collect and validate runtime settings.
        """

        self.drive = self.find_cdr_drive()
        self.opts = self.fetch_options()

    def run(self):
        """
        Compare all the directories.

        Break out of the outer loop after the first iteration,
        because diff takes care of the recursion.
        """

        for path, dirs, files in os.walk(self.opts.build):
            for directory in dirs:
                source = os.path.join(path, directory)
                if directory in self.SKIP:
                    continue
                elif directory == 'Inetpub':
                    target = self.drive + r":\Inetpub"
                else:
                    target = self.drive + ":\\cdr\\" + directory
                args = ["diff", self.opts.diffopts, source, target]
                if not self.opts.all:
                    args += ["-X", self.EXCLUDES]
                p = subprocess.Popen(args, **self.POPEN_OPTS)
                output, errout = p.communicate()
                if errout:
                    raise Exception(errout)
                for line in output.splitlines():
                    if not self.skip_line(line):
                        print(line)
            break

    def skip_line(self, line):
        line = line.replace("/", "\\").lower()
        if r"only in d:\inetpub\wwwroot: " in line:
            return True
        if r"only in d:\inetpub\wwwroot\cgi-bin\scheduler: static" in line:
            return True
        return False

    def fetch_options(self):
        """
        Parse and validate the command-line arguments.
        """

        desc = "Compare a CDR release set to the live file system"
        parser = argparse.ArgumentParser(description=desc)
        parser.add_argument("build", help="location of build files")
        parser.add_argument("--diffopts", "-o", default="-r")
        parser.add_argument("--all", "-a", action="store_true")
        return parser.parse_args()

    @staticmethod
    def find_cdr_drive():
        for drive in "DCEFGH":
            if os.path.isdir("{}:/cdr".format(drive)):
                return drive
        return None

Control().run()
exit(0)
