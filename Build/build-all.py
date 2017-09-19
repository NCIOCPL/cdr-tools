#!/Python/python.exe

"""
Assemble the files for a CDR release deployment.

This script was originally implemented for use with AnthillPro.
That tool was abandoned by CBIIT before we ever had an opportunity
to use it. The new tool du jour is Jenkins. The goal is to have
this script work correctly with or without Jenkins.

The original implementation pulled source code from the CBIIT
Subversion server. This rewrite uses GitHub repositories instead.

Only standard libraries are imported, to avoid dependencies on
things we might not have yet deployed.

JIRA::WEBTEAM-1884 - original implementation (Alan Meyer, April 2014)
JIRA::OCECDR-4300 - rewrite for Jenkins/GitHub (Bob Kline, September 2017)
"""

import argparse
import datetime
import logging
import os
import subprocess
import sys

class Control:
    """
    Master driver with runtime configuration settings for processing.
    """

    PIPE = subprocess.PIPE
    STDOUT = subprocess.STDOUT
    POPEN_OPTS = dict(shell=True, stdout=PIPE, stderr=STDOUT)

    def __init__(self):
        """
        Collect and validate runtime settings and set up logging.
        """

        self.dirs = Directory.all_dirs()
        self.drive = self.find_cdr_drive()
        self.opts = self.fetch_options()
        self.logger = self.make_logger()

    def run(self):
        """
        Generate the requested deployment package.
        """

        if not os.path.isdir(self.opts.base):
            os.makedirs(self.opts.base)
        for directory in self.dirs:
            directory.build(self)
            self.logger.info("built %s", directory.name)
        self.cleanup()
        self.logger.info("build complete")

    def fetch_options(self):
        """
        Parse and validate the command-line arguments.

        This method modifies the `dirs` attribute if --include or
        --exclude directories have been specified.
        """

        parser = self.make_argument_parser()
        opts = parser.parse_args()
        if "{branch}" in opts.base:
            opts.base = opts.base.format(branch=opts.branch)
        keys = dict([(d.name.lower(), d) for d in self.dirs])
        dirs = []
        if opts.include:
            for name in opts.include:
                directory = keys.get(name.lower())
                if not directory:
                    parser.error("unsupported directory %r" % name)
                dirs.append(directory)
            self.dirs = dirs
        elif opts.exclude:
            excludes = []
            for name in opts.exclude:
                if name not in keys:
                    parser.error("unsupported directory %r" % name)
                excludes.append(name.lower())
            excludes = set(excludes)
            for directory in self.dirs:
                if directory.name.lower() not in excludes:
                    dirs.append(directory)
            self.dirs = dirs
            if not self.dirs:
                parser.error("nothing left to build")
        return opts

    def make_argument_parser(self):
        """
        Specify the allowed/required command-line arguments.
        """

        dirlist = " ".join([d.name for d in sorted(self.dirs)])
        epilog = "valid arguments for --/include/--exclude:\n" + dirlist
        desc = "Assemble the files for a CDR release deployment"
        parser = argparse.ArgumentParser(description=desc, epilog=epilog)
        now = datetime.datetime.now()
        self.stamp = now.strftime("%Y%m%d%H%M%S")
        base = self.drive + ":/tmp/build/{branch}-" + self.stamp
        logpath = self.drive + ":/cdr/Log/build.log"
        parser.add_argument("branch", help="version control branch")
        parser.add_argument("-b", "--base", default=base, help="output base")
        parser.add_argument("-l", "--logpath", default=logpath,
                            help="where to record what we do")
        group = parser.add_mutually_exclusive_group()
        group.add_argument("-i", "--include", nargs="*",
                           help="directories to build")
        group.add_argument("-e", "--exclude", nargs="*",
                           help="directories to skip (not usable with -i)")
        return parser

    def make_logger(self):
        stream_handler = logging.StreamHandler()
        file_handler = logging.FileHandler(self.opts.logpath)
        format = "%(asctime)s [%(levelname)s] %(message)s"
        formatter = logging.Formatter(format)
        stream_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        logger = logging.getLogger("build")
        logger.setLevel("INFO")
        logger.addHandler(stream_handler)
        logger.addHandler(file_handler)
        self.log_config_settings(logger)
        return logger

    def log_config_settings(self, logger):
        logger.info("building %s", os.path.normpath(self.opts.base))
        logger.info("logging to %s", os.path.normpath(self.opts.logpath))
        if self.opts.exclude:
            logger.info("excluding %s", " ".join(self.opts.exclude))
        elif self.opts.include:
            logger.info("including %s", " ".join(self.opts.include))
        else:
            logger.info("building everything")

    def cleanup(self):
        script = self.drive + r":\cdr\Bin\fix-permissions.cmd"
        target = os.path.normpath(self.opts.base)
        args = script, target
        self.logger.info("fixing permissions")
        p = subprocess.Popen(args, **self.POPEN_OPTS)
        output, error = p.communicate()
        if p.returncode:
            self.logger.error("cleanup failure: {}".format(output))
            sys.exit(1)

    @staticmethod
    def find_cdr_drive():
        for drive in "DCEFGH":
            if os.path.isdir("{}:/cdr".format(drive)):
                return drive
        return None

class Directory:
    URL_BASE = "https://github.com/NCIOCPL/"
    BUILD_DIR = "build-directory.cmd"
    BUILD_BIN = "build-cdr-bin.cmd"
    BUILD_CLI = "build-client-files.cmd"
    SCRIPTS = os.path.split(os.path.abspath(sys.argv[0]))[0]
    def __init__(self, name, source=None):
        self.name = name
        self.source = source
    def build(self, control):
        drive = control.drive
        branch = control.opts.branch
        base = os.path.normpath(control.opts.base)
        if self.name == "Bin":
            script = os.path.join(self.SCRIPTS, self.BUILD_BIN)
            args = script, branch, base, drive
        elif self.name == "ClientFiles":
            script = os.path.join(self.SCRIPTS, self.BUILD_CLI)
            args = script, branch, base, drive, control.stamp
        else:
            url = self.URL_BASE + self.source.format(branch=branch)
            script = os.path.join(self.SCRIPTS, self.BUILD_DIR)
            args = script, url, base, self.name
        p = subprocess.Popen(args, **control.POPEN_OPTS)
        output, error = p.communicate()
        if p.returncode:
            control.logger.error("{}: {}".format(self.name, output))
            sys.exit(1)

    def __cmp__(self, other):
        return cmp(self.name.lower(), other.name.lower())

    @classmethod
    def all_dirs(cls):
        return [
            cls("Database", "cdr-server/branches/{branch}/Database"),
            cls("lib", "cdr-lib/branches/{branch}"),
            cls("Mailers", "cdr-publishing/branches/{branch}/Mailers"),
            cls("Publishing", "cdr-publishing/branches/{branch}/Publishing"),
            cls("Utilities", "cdr-tools/branches/{branch}/Utilities"),
            cls("Inetpub", "cdr-admin/branches/{branch}/Inetpub"),
            cls("Licensee", "cdr-publishing/branches/{branch}/Licensee"),
            cls("Scheduler", "cdr-scheduler/branches/{branch}"),
            cls("Glossifier", "cdr-glossifier/branches/{branch}"),
            cls("Emailers", "cdr-publishing/branches/{branch}/gpmailers"),
            cls("Schemas", "cdr-server/branches/{branch}/Schemas"),
            cls("Build", "cdr-tools/branches/{branch}/Build"),
            cls("Bin"),
            cls("ClientFiles"),
        ]

Control().run()
