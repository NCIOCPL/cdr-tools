#!/usr/bin/env python

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
import shutil
import subprocess
import sys

class Control:
    """
    Master driver with runtime configuration settings for processing.

    Class values:
      SCRIPTS - directory where the build scripts are stored
      POPEN_OPTS - options for launching a sub process

    Attributes:
      dirs - sequence of directory objects to be processed
      drive - letter representing the disk volume for the CDR
      opts - runtime control settings
      logger - object for recording what we do
    """

    SCRIPTS = os.path.split(os.path.abspath(sys.argv[0]))[0]
    POPEN_OPTS = dict(
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )

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

        self.fetch_branch()
        os.chdir(self.opts.base)
        for directory in self.dirs:
            directory.build(self)
            self.logger.info("built %s", directory.name)
        self.cleanup()
        self.logger.info("build complete")

    def fetch_branch(self):
        """
        Pull down the files from this branch of the CDR repositories.
        """

        path = os.path.abspath(os.path.join(self.opts.base, "branch"))
        if not os.path.isdir(path):
            os.makedirs(path)
        script = os.path.join(self.SCRIPTS, "fetch-branch.cmd")
        args = script, self.opts.branch, path
        p = subprocess.Popen(args, **self.POPEN_OPTS)
        output, error = p.communicate()
        if p.returncode:
            self.logger.error("failure fetching branch: {}".format(output))
            sys.exit(1)
        self.logger.info("fetched files for %s", self.opts.branch)

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
                parser.error("nothing to build")
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
        base = self.drive + ":/tmp/builds/{branch}-" + self.stamp
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
        """
        Create the object used to record what we do.

        The logger has two handlers, one to write to a disk log file,
        and the other to write to stderr.
        """

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
        """
        Record the options used for this build.
        """

        build_path = os.path.normpath(self.opts.base).replace("\\", "/")
        log_path = os.path.normpath(self.opts.logpath).replace("\\", "/")
        logger.info("building %s", build_path)
        logger.info("logging to %s", log_path)
        if self.opts.exclude:
            logger.info("excluding %s", " ".join(self.opts.exclude))
        elif self.opts.include:
            logger.info("including %s", " ".join(self.opts.include))
        else:
            logger.info("building everything")

    def cleanup(self):
        """
        Remove the working files/directories and fix the file permissions.
        """

        self.logger.info("removing temporary directories")
        shutil.rmtree(os.path.join(self.opts.base, "branch"))
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
        """
        Figure out which disk volume the CDR is installed on.
        """

        for drive in "DCEFGH":
            if os.path.isdir("{}:/cdr".format(drive)):
                return drive
        return None

class Directory:
    """
    Object representing a directory to be build for a CDR release.

    Class values:
      BUILD_CLI - script to build the ClientFiles directory

    Attributes:
      name - the name of the directory to be built
      source - relative path for the directory in the set
               pulled down from GitHub
    """

    BUILD_CLI = "build-client-files.cmd"

    def __init__(self, name, source=None):
        """
        Remember the directory name and optional source path.
        """

        self.name = name
        self.source = source

    def build(self, control):
        """
        Install this directory's portion of the build.

        The ClientFiles directory requires more complicated
        compilation and post-processing tasks, so we farm out the work
        to a separate command shell batch file. We can handle all the
        other directories by simply making a recursive copy of the
        files from the set retrieved from GitHub.

        """

        drive = control.drive
        base = os.path.normpath(control.opts.base)
        script = None
        if self.name == "ClientFiles":
            script = os.path.join(control.SCRIPTS, self.BUILD_CLI)
            args = script, base, drive, control.stamp
        else:
            source = os.path.join(control.opts.base, "branch", self.source)
            target = os.path.join(control.opts.base, self.name)
            shutil.copytree(source, target)
        if script is not None:
            p = subprocess.Popen(args, **control.POPEN_OPTS)
            output, error = p.communicate()
            if p.returncode:
                control.logger.error("{}: {}".format(self.name, output))
                sys.exit(1)

    def __lt__(self, other):
        """
        Make the directories sortable by name, ignoring case.

        We do this to make the usage help screen easier to read.
        """

        return self.sortkey < other.sortkey

    @property
    def sortkey(self):
        """
        Sort without regard to case.
        """

        if not hasattr(self, "_sortkey"):
            self._sortkey = self.name.lower()
        return self._sortkey

    @classmethod
    def all_dirs(cls):
        """
        Instantiate and return the sequence of all buildable directories.
        """

        return [
            cls("Database", "server/Database"),
            cls("lib", "lib"),
            cls("Mailers", "publishing/Mailers"),
            cls("Publishing", "publishing/Publishing"),
            cls("Utilities", "tools/Utilities"),
            cls("Inetpub", "admin/Inetpub"),
            cls("Licensee", "publishing/Licensee"),
            cls("Scheduler", "scheduler"),
            cls("glossifier", "glossifier"),
            cls("Schemas", "server/Schemas"),
            cls("Filters", "server/Filters"),
            cls("Build", "tools/Build"),
            cls("Bin", "tools/Bin"),
            cls("api", "server/api"),
            cls("ClientFiles"),
        ]

if __name__ == "__main__":
    "Top-level entry point."
    Control().run()
