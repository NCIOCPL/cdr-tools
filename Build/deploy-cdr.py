#!/usr/bin/env python

"""
Deploy a CDR patch or release on a Windows CDR server.

This script was originally implemented for use with AnthillPro.
That tool was abandoned by CBIIT before we ever had an opportunity
to use it. The new tool du jour is Jenkins. The goal is to have
this script work correctly with or without Jenkins.

It is assumed that the files deployed by the script have been
prepared by running `build-all.py`.

JIRA::WEBTEAM-1884 - original implementation (Alan Meyer, April 2014)
JIRA::OCECDR-4300 - rewrite for Jenkins/GitHub (Bob Kline, September 2017)
"""

import argparse
import logging
import os
import shutil
import subprocess
import sys
import time


class Control:
    """
    Master driver with runtime configuration settings for processing.

    Class values:
      SERVICES - things we need to suspend in order to replace the files
      POPEN_OPTS - options for launching a sub process

    Attributes:
      dirs - sequence of directory objects to be processed
      tier - which hosting environment server we're running on
      drive - letter representing the disk volume for the CDR
      opts - runtime control settings
      logger - object for recording what we do
    """

    SERVICES = "CDRScheduler", "W3SVC"
    POPEN_OPTS = dict(
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )

    def __init__(self):
        """
        Collect and validate runtime settings and set up logging.

        Fetching the tier also sets self.drive as a side effect.
        """

        self.dirs = self.Directory.all_dirs()
        self.tier = self.get_tier()
        self.opts = self.fetch_options()
        self.logger = self.make_logger()

    def run(self):
        """
        Install the directories present in the build.

        If we running in live mode, we suspend the CDR services while
        we work.
        """

        self.stop_services()
        for path, dirs, files in os.walk(self.opts.source):
            while dirs:
                name = dirs.pop(0)
                directory = self.dirs.get(name.lower())
                if directory:
                    directory.install(self)
                    self.logger.info("installed %s", directory.name)
                elif name.lower() != "emailers":
                    self.logger.warning("%s not supported", name)
        if not self.opts.test:
            self.start_services()
        self.logger.info("deployment complete")

    def stop_services(self):
        """
        Stop the CDR services in reverse order if this is a live run.

        As a side effect, create a test destination directory if
        appropriate.

        Pause for a few seconds after stopping the services to let
        the dust settle.
        """

        if self.opts.test:
            self.logger.info("services not stopped (test run)")
            if not os.path.isdir(self.opts.test):
                os.makedirs(self.opts.test)
                self.logger.info("created %s", self.opts.test)
        else:
            self.logger.info("stopping services")
            self.services = [self.Service(s, self) for s in self.SERVICES]
            for service in reversed(self.services):
                if not service.running():
                    self.logger.warning("%s already stopped", service.name)
                else:
                    service.stop()
            time.sleep(5)

    def start_services(self):
        """
        Restart the CDR services.

        We restart the CDR service first, and then the CDR Scheduler service.
        In contrast with the previous implementation of this script, we
        restart the services whether they were started to begin with or
        not. On the other hand, if the script exits with an error before
        we get to this point, the operator will need to make a determination
        as to whether it is appropriate to restart the services, and if so,
        do it by hand. It is not necessarily safe to restart the services
        (particularly the scheduling service) in the wake of a broken
        deployment.

        [Note: as of the Gauss release, the CDR service is no longer used.]
        """

        for service in self.services:
            if service.name.upper() != "CDR":
                service.start()
                self.logger.info("started %s service", service.name)

    def fetch_options(self):
        """
        Parse and validate the command-line arguments.
        """

        desc = "Deploy a CDR release set"
        parser = argparse.ArgumentParser(description=desc)
        logpath = self.drive + r":\cdr\Log\deploy.log"
        parser.add_argument("source", help="location of deployment files")
        parser.add_argument("-t", "--test", metavar="DESTINATION",
                            help="write here instead of live CDR system")
        parser.add_argument("-o", "--overlay", action="store_true",
                            help="don't remove existing files/directories")
        parser.add_argument("-l", "--logpath", default=logpath)
        return parser.parse_args()

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
        logger.info("running on %s", self.tier)
        logger.info("deploying from %s", self.opts.source)
        if self.opts.test:
            target = self.opts.test.replace("\\", "/")
            logger.info("performing test deployment to %s", target)
        logger.info("logging to %s", self.opts.logpath.replace("\\", "/"))
        return logger

    def fix_permissions(self, target):
        """
        Adjust the permissions on a set of deployed files.

        Log any problems as warnings but don't abort processing.
        """

        args = self.drive + r":\cdr\Bin\fix-permissions.cmd", target
        result = self.execute(args)
        if result.code:
            self.logger.warning("%s: %s", target, result.output)

    @classmethod
    def execute(cls, args):
        """
        Run an external program and return the results.
        """

        p = subprocess.Popen(args, **cls.POPEN_OPTS)
        output, error = p.communicate()

        class Result:
            def __init__(self, code, output):
                self.code = code
                self.output = output
        return Result(p.returncode, output)

    def get_tier(self):
        """
        Figure out which CDR tier we're running on.

        As a beneficial side effect, we also learn (and remember)
        which drive volume the CDR is installed on.
        """

        self.drive = None
        for drive in "DCEFGH":
            path = "{}:/etc/cdrtier.rc".format(drive)
            if os.path.isfile(path):
                self.drive = drive
                tier = open(path).read().strip()
                return tier
        raise Exception("unable to find CDR drive or tier")

    class Service:
        """
        Windows CDR service which needs to be suspended.

        If we don't stop the services while we deploy the new
        set of files, the deployment will fail because the services
        will have some of the files we need to replace locked.
        This isn't necessary if we're doing a test run installing
        the files in a location other than where the live CDR
        runs from.

        Attributes:
          name - internal name for the service (not the display name)
          nssm - path to the service manager program
        """

        def __init__(self, name, control):
            """
            Save the internal name of the service and the NSSM path.
            """

            self.name = name
            self.logger = control.logger
            self.nssm = control.drive + r":\cdr\Bin\nssm.exe"

        def control(self, option):
            """
            Common code to invoke the service manager.

            If the command fails, log the problem and exit.

            Pass:
              option - string for the command to invoke

            Return:
              output of the command
            """

            args = self.nssm, option, self.name
            result = Control.execute(args)
            output = str(result.output, "utf-16").strip()
            if result.code:
                command = " ".join(args)
                self.logger.error("%s: %s", command, output)
                sys.exit(1)
            return output

        def running(self):
            """
            Ask the service manager whether the service is started.
            """

            return "SERVICE_RUNNING" in self.control("status")

        def start(self):
            """
            Start the service and pause before continuing.

            Had problems with `self.control("start")` running into
            unexpected 'PENDING' output, so switched to NET START ....
            """

            if not self.running():
                args = "NET", "START", self.name
                result = Control.execute(args)
                if result.code:
                    command = " ".join(args)
                    self.logger.error("%s: %s", command, result.output)
                    sys.exit(1)
                time.sleep(2)

        def stop(self):
            """
            Ask the service manager to stop the service.
            """

            if self.running():
                args = "NET", "STOP", self.name
                result = Control.execute(args)
                if result.code:
                    command = " ".join(args)
                    self.logger.error("%s: %s", command, result.output)
                    sys.exit(1)
                if self.name.upper() == "CDR":
                    args = r"d:\cdr\bin\ShutdownCdr.exe", "bkline", ""
                    Control.execute(args)
                time.sleep(2)

    class Directory:
        """
        A piece of the build set to be deployed.

        Class values:
          WWW_CLEAN - web server directories to be replaced completely
                      (unless the --overlay option is set)

        Attributes:
          name - the name of the directory to be deployed
        """

        WWW_CLEAN = "cgi-bin", "images", "js", "stylesheets"

        def __init__(self, name):
            "Save the directory name."
            self.name = name

        def install(self, control):
            """
            Route the web server's files to special handling.

            Everything else is pretty much a straight copy.
            """

            if self.name == "Inetpub":
                self.install_inetpub_files(control)
            else:
                self.install_directory(control)

        def install_directory(self, control):
            """
            Copy the files from the build set.

            By default, we drop the directory and re-create it
            from the build set. This can be overridden with the
            --overlay option, which copies the build set over
            the existing location, leaving in place any files
            or subdirectories which were present in the target
            location but not in the build set.

            Note: we discovered when deploying Ising to QA that
            Windows didn't really do what it was asked all the
            time by the `shutil.rmtree()` call. Hence the more
            robust loop which checks to make sure the old files
            and directories are gone before proceeding.
            """

            source = os.path.join(control.opts.source, self.name)
            target = os.path.join(control.drive + r":\cdr", self.name)
            if control.opts.test:
                target = os.path.join(control.opts.test, "cdr", self.name)
            if control.opts.overlay and os.path.exists(target):
                self.copy(source, target)
            else:
                tries = 10
                pattern = "removing %s (%d tries left)"
                while os.path.exists(target):
                    if not tries:
                        raise Exception("can't remove {!r}".format(target))
                    control.logger.info(pattern, target, tries)
                    shutil.rmtree(target)
                    tries -= 1
                    time.sleep(2)
                shutil.copytree(source, target)
            control.fix_permissions(target)

        def install_inetpub_files(self, control):
            r"""
            Replace the Inetpub/wwwroot tree.

            This directory requires special handling for three reasons:
             1. there are a bunch of files not under version control
             2. some files differ from tier to tier (e.g. the favicon)
             3. all the other directories are installed under \cdr
                except this one.
            """

            source = os.path.join(control.opts.source, "Inetpub", "wwwroot")
            target = os.path.join(control.drive + r":\Inetpub", "wwwroot")
            if control.opts.test:
                target = os.path.join(control.opts.test, "Inetpub", "wwwroot")
            if not os.path.exists(target):
                shutil.copytree(source, target)
            else:
                if not control.opts.overlay:
                    for name in self.WWW_CLEAN:
                        path = os.path.join(target, name)
                        if os.path.exists(path):
                            shutil.rmtree(path)
                self.copy(source, target)
            if control.tier:
                favicon = os.path.join(target, "favicon.ico")
                tiericon = os.path.join(target,
                                        "favicon-{}.ico".format(control.tier))
                shutil.copy(tiericon, favicon)
            control.fix_permissions(target)

        def copy(self, what, where):
            """
            Recursively copy a directory.

            We can't use `shutil.copytree()` when the target directory
            already exists, because that function requires that the
            destination does not already exist. So we implement our
            own logic.
            """

            if os.path.isdir(what):
                if not os.path.isdir(where):
                    os.makedirs(where)
                files = os.listdir(what)
                for f in files:
                    source = os.path.join(what, f)
                    destination = os.path.join(where, f)
                    self.copy(source, destination)
            else:
                shutil.copyfile(what, where)

        @classmethod
        def all_dirs(cls):
            """
            Return a dictionary of all the directories we support.

            The keys are the lowercase names of the directories.
            """

            dirs = [
                cls("Database"),
                cls("lib"),
                cls("Mailers"),
                cls("Publishing"),
                cls("Utilities"),
                cls("Inetpub"),
                cls("Licensee"),
                cls("Scheduler"),
                cls("Schemas"),
                cls("Filters"),
                cls("Build"),
                cls("Bin"),
                cls("api"),
                cls("ClientFiles"),
            ]
            return dict([(d.name.lower(), d) for d in dirs])


if __name__ == "__main__":
    "Top-level entry point."
    Control().run()
