#----------------------------------------------------------------
# Create all of the application program files required for the deployment
# of the CDR on a Windows server.
#
# The program may be run by a person using the command line, or may be
# run by the AnthillPro or other build automation software.
#
# The output of the program is a collection of files that will be deployed
# to one or more Windows servers using separate scripts.
#
# Note: No use is made of cdr specific python libraries.
#
# BZIssue::None  (JIRA::WEBTEAM-1884)
#
#                                               Alan Meyer, April, 2014
#----------------------------------------------------------------
import sys, os, time, getopt, re, atexit, BuildDeploy as bd

# Global constants
TOK_PAT = re.compile(r'\"([^\"]*)\"|([^\s\"]*)')

def exitFunc():
    """
    Invoked when program exits from any sys.exit() call.
    """
    if 'Cfg' in globals():
        cwd = os.getcwd()
        if cwd != Cfg.startpath:
            bd.log("Changing current directory back from:\n   %s\nto:\n   %s" %
                 (cwd, Cfg.startpath))
            os.chdir(Cfg.startpath)

def usage(msg=None):
    """
    Print usage message to stdout and exit.  No logging.

    Pass:
        msg - Optional error message to include
    """
    global Cfg

    print("""
Prepare program files and scripts for deployment to a Windows CDR server.

usage: %s {options}

 options:

 --drive letter      - Drive letter (with or without ':') to prepend to
                       paths.  All paths are relative to this drive unless
                       explicitly defined with a fully qualified name.
                       Default = logged in drive, currently '%s'.
 --srcpath  dirpath  - Base directory path for external scripts.
                       Default ='%s'
 --basepath dirpath  - Base directory path for output files.
                       Default now='%s'
 --linuxpath dirpath - Base directory path for Linux output files.
                       Default now='%s'
 --parmfile filepath - Path to parameter file containing all parameters.
                       This is an alternative to passing many parms on a
                       hand typed command line.  Format is:
                         --optname1 optval1
                         --optname2 optval2
                         ...
                         source_directory
                       Program processes all command line args first, then
                       reads parmfile, if any, and overrides whatever we
                       have so far.
                       Blank lines and comments beginning with '#' are okay.
                       No default.
 --logfile  filepath - Path to output logfile, default=%s.
 --include  dirname  - Single CDR directory to build.  May be invoked
                       multiple times.  If no --include parameters are passed,
                       all CDR directories will be built, else
                       only --include dirs are created.
                       Dirnames are matched against the internal list of
                       dirnames that can be built.  Current values are:
%s
 --exclude  dirname  - CDR directories NOT to be built.  May be invoked
                       multiple times.  Makes sense only if no --includes
                       and no --execcmds.
 --svnurl   url      - URL to svn repository, default=
                       %s
 --svnuser  userid   - Subversion userid if not using cached credentials.
                       No default.
 --svnpw    password - Subversion password if not using cached credentials.
                       No default.
 --svnbrnch name     - Subversion branch to holding source code.  Required!
                       Examples: 'trunk', 'branches/Bohr', etc.  No default.
 --execcmd "command" - Ignore the built in command list and execute this
                       command.  Use "--helpcmds" for semantics and examples.
                       May be invoked multiple times.
                       Default is to use the commands built in to the script.
 --failok            - If a command returns an error or stderr info, log it
                       but continue to the next command.
                       If initial conditions fail we ignore --failok and abort
                       Default=Abort on any error.
 --trialrun          - Log, but do not execute, all commands.  Shows what
                       will be done and may show some errors that would
                       otherwise not show up until later on.  Default='false'.
 --mindisk  number   - Refuse to execute if the amount of diskspace available
                       at basepath is less than the specified number of
                       gigabytes.  Default = %s.
 --helpcmds            Display help for how to specify executable commands.
 --help              - Display this usage message and quit.

If the argument for a parameter consists of more than one word, double quotes
around the entire argument are required, for example:
     --execcmd "copy /Y file1 file2"
""" % (os.path.basename(sys.argv[0]), Cfg.drive, Cfg.srcpath, Cfg.basepath,
       Cfg.linuxpath, Cfg.logfile, Cfg.dirList, Cfg.svnurl, Cfg.mindisk))

    if msg:
        sys.stderr.write("\nERROR: %s\n" % msg)
    sys.exit(1)

def helpcmds():
    """
    Display a help message for commands.
    """
    print("""
Commands may be specified with the --execcmds parameter, either on the command
line or in a parameter file specified with --parmfile.

Commands are strings with the following format:

   command arg1
 or:
   command "arg1 arg2 ... argN"

Commands may be fully qulified, e.g., "d:/.../..." or relative to the basepath.

Arguments can have prefixes refering to parameters taken from the command
line or parmfile.  Valid prefixes are "@+" to make an argument available to a
command as an environment variable and "@-" to make it available as a
command line argument.  For example:

  @+svnbrnch = Store the value of --svnbrnch in an environment variable
               before executing the command.  See below for elaboration.
  @-svnbrnch = Pass the value of --svnbrnch as a command line argument.

Sometimes arguments need to be paired, for example, a script might expect
something like the following to occur together or not at all.

  --svnuid @-svnuser

If no value has been passed to our top level script for --svnuser, then
neither term should appear in the command to run.  We might expect either

  runthis.cmd --uid alan
or:
  runthis.cmd
but never:
  runthis.cmd --uid

To achieve this, group the fixed part and the variable part with parentheses
and separate them with a forward slash ('/', no spaces).  For example:

  python "example.py @+svnbrnch (--uid/@-svnuser) (--pw/@-svnpw) arg1 arg2"

Here is what occurs after parameter substitution:

  If:

     self.svnbrnch = "branches/Einstein"
     self.svnuser  = "albert"
     self.svnpw    = "relativity"

  Then the equivalent of the following will execute:

     REM Prefix "CDRBUILD_" to env var to simulate a namespace.
     SET CDRBUILD_SVNBRNCH=branches/Einstein
     python example.py --uid albert --pw relativity arg1 arg2

  If no values were set for self.svnuser or self.svnpw then the following
  executes:

     SET CDRBUILD_SVNBRNCH=branches/Einstein
     python example.py arg1 arg2
""")
    sys.exit(1)

def showConfig():
    """
    Create a list of current configuration values, i.e., members of this
    class.

    Return:
        Formated list suitable for logging, one parm per line.
    """
    global Cfg

    # Are there any commands to execute (--execcmd)
    if Cfg.execcmd is not None:
        cmdList = "\n " + "\n ".join(Cfg.execcmd)
    else:
        cmdList = "None"

    output = """
%s

Build parameters:

 --srcpath:   %s
 --basepath:  %s
 --linuxpath: %s
 --parmfile:  %s
 --logfile:   %s
 --include:   %s
 --exclude:   %s
 --svnurl:    %s
 --svnuser:   %s
 --svnbrnch:  %s
 --execcmds:  %s
 --failok;    %s
 --trialrun:  %s
 --mindisk:   %d GB
 free disk:   %d GB

""" % (bd.versionCtlVersion(sys.argv[0]),
       Cfg.srcpath, Cfg.basepath, Cfg.linuxpath, Cfg.parmfile, Cfg.logfile,
       Cfg.includes, Cfg.excludes, Cfg.svnurl, Cfg.svnuser, Cfg.svnbrnch,
       cmdList, Cfg.failok, Cfg.trialrun, Cfg.mindisk, Cfg.freedisk)

    return output

class Config:
    """
    Container class to hold all configuration information.
    Instantiate exactly one global instance as Cfg.
    """

    def __init__(self):
        """
        Set default values for all configuration settings.

        Drive letters will be prepended to paths later.
        """
        self.current  = time.strftime("%Y-%m-%d_%H-%M-%S")
        self.drive    = os.getcwd()[0]
        self.basepath = "\\tmp\\CdrBuild\\%s" % self.current
        self.linuxpath= self.basepath # distinguished from basepath later
        self.parmfile = None
        self.logfile  = "\\cdr\\Log\\build.log"
        self.includes = None
        self.excludes = None
        self.svnurl   = 'https://ncisvn.nci.nih.gov/svn/oce_cdr'
        self.svnuser  = None
        self.svnpw    = None
        self.svnbrnch = None
        self.srcpath  = os.getcwd()
        self.startpath= self.srcpath
        self.execcmd  = None
        self.failok   = False
        self.trialrun = False
        self.mindisk  = 5
        self.freedisk = -1
        self.custom_linuxpath = self.custom_basepath = False

        # Command line options
        self.longOpts = ["basepath=", "linuxpath=",
                         "srcpath=", "drive=", "parmfile=",
                         "logfile=", "include=", "exclude=",
                         "svnuser=", "svnpw=", "svnbrnch=",
                         "svnurl=", "mindisk=", "execcmd=",
                         "failok", "trialrun", "helpcmds", "help"]

        # Commands to execute for a full build
        # See --helpcmds for explanation

        # Start with the svn options split up, because build-pythondir.cmd
        # expects the basepath argument in the middle of them.
        svn_opts = ["@+svnurl @-svnbrnch", "@-svnpw @-svnuser"]

        # build_python_dir is a string interpolation pattern (using %s).
        # build-pythondir.cmd is a bit of a misnomer (Licensee isn't really
        # a Python directory, though it does have one Python script in it).
        build_python_dir = " ".join(("build-pythondir.cmd",
                                     svn_opts[0],
                                     "@-basepath %s ",
                                     svn_opts[1]))

        # build_linux_dir works much the same way as build_python_dir
        build_linux_dir = " ".join(("build-linuxdir.cmd",
                                    svn_opts[0],
                                    "@-linuxpath %s",
                                    svn_opts[1]))

        # Splice the svn options back together.
        svn_opts = " ".join(svn_opts)
        self.commandList = [
            ["Bin", "build-cdr-bin.cmd @+basepath %s" % svn_opts],
            ["ClientFiles", "build-client-files.cmd @+basepath %s" % svn_opts],
            ["Database", build_python_dir % "Database"],
            ["lib", build_python_dir % "lib"],
            ["Mailers", build_python_dir % "Mailers"],
            ["Publishing", build_python_dir % "Publishing"],
            ["Utilities", build_python_dir % "Utilities"],
            ["Inetpub", build_python_dir % "Inetpub"],
            ["Licensee", build_python_dir % "Licensee"],
            ["Scheduler", build_python_dir % "Scheduler"],
            ["Glossifier", build_linux_dir % "Glossifier"],
            ["Emailers", build_linux_dir % "Emailers"],
            ["FTP", build_linux_dir % "FTP"]
        ]
        self.dirList = [dir[0] for dir in self.commandList]

    def getParms(self):
        """
        Get and validate parameters for the run.
        """
        # From command line
        self.cmdParse()

        # From a config file
        if self.parmfile is not None:
            self.cmdFile()

        # Validate
        # ISSUE: What if I want to checkout all the build source?
        bd.chkPath(self.srcpath, isDir=True)
        # usage("Missing required argument, source_directory")

    def cmdParse(self):
        """
        Parse the command line.

        The only validation done here is validation that can't be postponed.
        """
        global Cfg

        # Parse command line
        try:
            (opts, args) = getopt.getopt(sys.argv[1:], "", self.longOpts)
        except getopt.GetoptError as e:
            usage(str(e))

        # Pass one to get args from command file, if any
        cmdArgs = []
        for opt, arg in opts:
            if opt == "--help":
                usage()
            if opt == "--helpcmds":
                helpcmds()

            if opt == "--parmfile":

                # Check for named file
                if not arg:
                    usage("--parmfile requires parameter file name argument")
                if not bd.chkPath(arg):
                    usage('Parameter file "%s" not found' % arg)

                # Get parsed contents of the parameter file as array of tokens
                self.parmfile = arg
                cmdArgs = self.cmdFile()

        # Combine any parameters from cmd file and cmd line and re-parse
        # This causes parmfile parms to be read first and overridden by
        #  any parms on the command line
        cmdArgs.extend(sys.argv[1:])
        try:
            (opts, args) = getopt.getopt(cmdArgs, "", self.longOpts)
        except getopt.GetoptError as e:
            usage(str(e))

        # DEBUG
        # print("cmdArgs=%s" % cmdArgs)
        # print("opts=%s" % opts)
        # print("args=%s" % args)

        # Pass 2: Process any parm file args followed by sys args
        for opt, arg in opts:

            if opt == "--srcpath":
                if not bd.chkPath(arg, isDir=True):
                    bd.fatal('"--srcpath %s" not found' % arg)
                self.srcpath = arg
                self.startpath = os.getcwd()
                bd.log("Changing current directory from:\n   %s\nto:\n   %s" %
                     (self.startpath, self.srcpath))
                os.chdir(self.srcpath)

            if opt == "--basepath":
                # we'll create this later, so isn't this test inappropriate???
                #if not bd.chkPath(arg, isDir=True):
                #    bd.fatal('"--basepath %s" not found' % arg)
                self.basepath = arg
                self.custom_basepath = True

            if opt == "--linuxpath":
                self.linuxpath = arg
                self.custom_linuxpath = True

            if opt == "--drive":
                # Convert "c:" to "c", etc.
                self.drive = arg[0]

            if opt == "--parmfile":
                # Only allow one parmfile, must be on command line
                if self.parmfile and arg != self.parmfile:
                    usage("Only one --parmfile allowed")

            if opt == "--logfile":
                self.logfile = arg

            if opt == "--include":
                if self.includes is None:
                    self.includes = []
                self.includes.append(arg)

                # Override any previously encountered exclude
                if self.excludes:
                    for i in range(len(self.excludes)):
                        if self.excludes[i] == arg:
                            del(self.excludes[i])
                            break

            if opt == "--exclude":
                if self.excludes is None:
                    self.excludes = []
                self.excludes.append(arg)

                # Override any previously encountered include
                if self.includes:
                    for i in range(len(self.includes)):
                        if self.includes[i] == arg:
                            del(self.includes[i])
                            break

            if opt == "--svnbrnch":
                self.svnbrnch = arg

            if opt == "--svnurl":
                self.svnurl = arg

            if opt == "--svnuser":
                self.svnuser = arg

            if opt == "--svnpw":
                self.svnpw = arg

            if opt == "--execcmd":
                if self.execcmd is None:
                    self.execcmd = []
                self.execcmd.append(arg)

            if opt == "--failok":
                self.failok = True

            if opt == "--trialrun":
                self.trialrun = True

            if opt == "--mindisk":
                self.mindisk = int(arg)

        # Modify basepath and linuxpath to indicate source of this data.
        # If custom paths are set, honor them.
        if self.custom_basepath and not self.custom_linuxpath:
            self.linuxpath = self.basepath
        if self.svnbrnch:
            brnchName = self.svnbrnch.replace("\\", "_").replace("/", "_")
            if not self.custom_basepath:
                self.basepath += "_%s" % brnchName
            if not self.custom_linuxpath:
                self.linuxpath += "_%s" % brnchName
        if not self.custom_basepath:
            self.basepath += "_windows"
        if not self.custom_linuxpath:
            self.linuxpath += "_linux"

        # Normalize all paths separators and drive letters
        self.srcPath  = self.normPath(self.srcpath)
        self.basepath = self.normPath(self.basepath)
        self.parmfile = self.normPath(self.parmfile)
        self.logfile  = self.normPath(self.logfile)
        self.linuxpath= self.normPath(self.linuxpath)

        # Now that we have a final basepath, we can calculate disk space
        self.freedisk = bd.availDiskGB(self.basepath)

    def normPath(self, path):
        """
        Normalize path names to use Windows path separators and drive letters.

        Pass:
            Pathname to normalize.

        Return:
            Normalized pathname.
        """
        if not path:
            return path

        # Make the path usable for the build.
        return bd.windowsPath(os.path.abspath(path))

    def cmdFile(self):
        """
        Retrieve arguments from a parameter file and return them in
        a format compatible with getopt.getopt().

        Parameter file contains:

            Optional blank lines
            Optional comment lines with leading '#'
            Program options with or without args, e.g.:
                --basepath d:/home/alan/build
                --logfile d:/home/alan/temp
            Do not put anything else on the line

        Return:
            Array of values, some --option, some values of options, just
            like argv.
        """
        # Read in the parms
        try:
            fp = open(self.parmfile, "r")
        except IOError as e:
            usage("Cannot open parmfile\n%s" % str(e))
        lines = fp.readlines()
        fp.close()

        # Parse
        args = []
        for line in lines:

            # Leading and trailing blanks
            line = line.strip("\n \t")

            # Empty line
            if not line:
                continue

            # Comment
            if line[0] == '#':
                continue

            # Get values, treating quoted strings as single value
            # Values can only be a parameter name and a value, not more
            # Up to two values on a line
            matches = TOK_PAT.findall(line)
            if len(matches) < 1:
                bd.fatal('Unexpected values in parm file: "%s"' % line)

            # The pattern produces pairs of ('',val) or (val,'')
            lineArgs = []
            for match in matches:
                if match[0]:
                    lineArgs.append(match[0])
                elif match[1]:
                    lineArgs.append(match[1])

            if len(lineArgs) > 2:
                bd.fatal('Too many tokens on parmfile line: "%s"' % line)

            args.extend(lineArgs)

        return args

    def okayToStart(self):
        """
        Perform any tests that can be performed up front in order to avoid
        performing a partial build that then aborts with a foreseeable error.

        All logging is done to stderr and log file, but we do not abort until
        the end.
        """
        # No problems yet
        allOk = True

        # Minimum  disk free space we want
        if self.freedisk < 0:
            bd.log("Warning: Unable to determine free disk space at %s" %
                 self.basepath, bd.STDERR)
        elif self.freedisk < self.mindisk:
            bd.log("%d GB disk space < than minimum %d GB specified" %
                    (self.freedisk, self.mindisk), bd.STDERR)
            allOk = False;

        # Includes and excludes are okay?
        if self.includes is not None:
            for dir in self.includes:
                if dir not in self.dirList:
                    bd.log("--include %s, '%s' not in list of dirs to process" %
                        (dir, dir), bd.STDERR)
                    allOk = False
        if self.excludes is not None:
            for dir in self.excludes:
                if dir not in self.dirList:
                    bd.log("--exclude %s, '%s' not in list of dirs to process" %
                         (dir, dir), bd.STDERR)
                    allOk = False

        # Subversion URL, just a simple check here
        if not self.svnurl.startswith("http"):
            bd.log("Invalid svn url: %s" % self.svnurl, bd.STDERR)
            allOk = False

        # Subversion branch is required
        if not self.svnbrnch:
            usage("Subversion branch (--svnbrnch) is required")

        # Abort on errors here.  Even a trial run would be a mistake
        if not allOk:
            bd.fatal("Errors found in startup configuration")

    def setFinalCmds(self):
        """
        Examine the hard wired command list, includes, excludes, and
        execcmds in order to produce a list of commands to execute.

        Output is an array of command strings stored in self.finalCmdList
        """
        # This is the final list of commands to execute
        self.finalCmdsList = []

        # If there are any includes, put them in
        # Any excludes specified in a parm file have already been
        # overridden by any includes specified on the command line.
        # See cmdParse().
        if self.includes:
            for inc in self.includes:
                for cmd in self.commandList:
                    if cmd[0] == inc:
                        self.finalCmdsList.append(cmd[1])

        # Add any execcmds
        if self.execcmd:
            for exe in self.execcmd:
                self.finalCmdsList.append(exe)

        # If nothing specified by --include or --exec, copy in the defaults
        if not self.finalCmdsList:

            # Subtract any excludes from the default list
            if self.excludes:
                for exc in self.excludes:
                    listIndex = len(self.commandList) - 1
                    while listIndex >= 0:
                        if self.commandList[listIndex][0] == exc:
                            del(self.commandList[listIndex])
                        listIndex -= 1

            # Dump everything else into the final commands
            self.finalCmdsList = [cmd[1] for cmd in self.commandList]


#----------------------------------------------------------------
#                MAIN
#----------------------------------------------------------------
atexit.register(exitFunc)
Cfg = Config()

# Replace defaults with args for this run
Cfg.getParms()

# Before this, logging is to the default log in BuildDeploy.py
bd.setLogfileName(Cfg.logfile)

# Check free disk
Cfg.freedisk = bd.availDiskGB(Cfg.basepath)

# Produce the final list of commands to execute
Cfg.setFinalCmds()
if not Cfg.finalCmdsList:
    bd.fatal("No commands found to run")

bd.log("""
=====================================================================
                           Building CDR
=====================================================================

%s""" % showConfig())

# Check initial conditions
Cfg.okayToStart()

# Create the output directories
if not Cfg.trialrun:
    paths = set()
    for cmd in Cfg.finalCmdsList:
        if "basepath" in cmd:
            paths.add(Cfg.basepath)
        elif "linuxpath" in cmd:
            paths.add(Cfg.linuxpath)
    for path in paths:
        if not bd.chkPath(path, True):
            try:
                bd.makeDirs(path)
            except Exception as e:
                bd.fatal("Unable to create output directory: %s:\n%s" %
                         (path, str(e)))

# Run them
if Cfg.finalCmdsList:
    for cmd in Cfg.finalCmdsList:
        bd.runCmd(cmd, Cfg, Cfg.trialrun, Cfg.failok)

# Done
bd.log("""
=====================================================================
                           Build Complete
=====================================================================
""")
