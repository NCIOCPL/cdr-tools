#----------------------------------------------------------------
# Include module for build and deploy processes containing common routines.
# Note: No use is made of cdr specific python libraries.
#
# BZIssue::None  (JIRA::WEBTEAM-1884)
#
#                                               Alan Meyer, May, 2014
#----------------------------------------------------------------
import sys, os, re, time, subprocess

STDOUT  = "stdout"
STDERR  = "stderr"
INVALID = '@@INVALID@@'
CR_PAT  = re.compile(r'\r+\n')

# The drive letter for output
# Call setDrive() if required BEFORE anything else for best result
DRV     = 'd'

# Value indicating that no return code produced by a subprocess command
# My testing in Windows 7 could not make this happen when calling a cmd file
NO_RETURN = "No return code found"

# This file holds any error messages generated before the build or deploy
# programs have initialized the logfile for their purposes.
# Writes to the current drive
LF = "/cdr/log/BuildDeploy.log"

def setDrive(driveLetter):
    """
    Set the drive letter for operations.  Used, for example to build or
    deploy a CDR instance on c: instead of the usual d:.

    Fatal error if x:\ does not exist where x == driveLetter.

    Pass:
        driveLetter - Letter to use.  No colon, just single letter.
    """
    global DRV

    # Is this drive letter valid?
    # If not, fatal error messages go to default drive letter
    path = "%s:\\" % driveLetter
    if not chkPath(path, True):
        fatal("Unable to find a file system on drive letter '%s'" %
               driveLetter)

    DRV = driveLetter

def getDrive():
    """
    Return the current value of DRV.
    """
    global DRV
    return DRV

def setLogfileName(fname):
    """
    Set the logfile name to something other than the default.  Should
    only be called before the first call to log.

    Pass:
        fname - New filename.
    """
    global LF

    # Test
    try:
        fp = open(fname, "a")
        fp.close()
    except Exception as e:
        fatal("Could not open logfile '%s' for append: %s" % (fname, str(e)))

    LF = fname

def log(msg, dest=STDOUT, fatal=False):
    """
    Log a message to CDR specific log files and to stdout or stderr.
    If run via AnthillPro, stdout and stderr will be logged by AnthillPro
    to its own log destinations.

    Pass:
        msg   - Message to be logged.
        dest  - STDOUT or STDERR.
        fatal - True = Log an abort message and terminate the program.
    """
    global LF

    # Handle unicode clumsily, but without crashing
    if type(msg) == type(u""):
        msg = msg.encode('utf-8', 'replace')

    # Clean artifacts from capturing output of subcommands
    msg = CR_PAT.sub("\n", msg)

    # Log it
    logF = None
    try:
        logF = open(LF, "a")
    except Exception as e:
        sys.stderr.write('Message was: %s\n' % msg)
        sys.stderr.write(
            'Unable to open logfile "%s" for append: %s - Aborting!\n'
                          % (LF, str(e)))
        sys.exit(1)

    # Valid sink?
    if dest not in (STDOUT, STDERR):
        msg  = "Message logged to stderr instead of invalid '%s'\n%s\n" % \
               (dest, msg)
        dest = sys.stderr

    if fatal:
        msg += "\nAborting after FATAL error!\n"

    # Show to higher level
    if dest == STDOUT:
        print("%s" % msg)
    else:
        sys.stderr.write("%s\n" % msg)

    # Log it
    logF.write("--- %s --- To %s:\n%s\n" % (time.ctime(), dest, msg))
    logF.flush()

    if fatal:
        logF.write("""
=====================================================================
                        Aborted on Fatal Error
=====================================================================
""")
    logF.close()

    if fatal:
        sys.exit(1)

def fatal(msg):
    """
    Log fatal error message to stderr and log.

    Pass:
        msg - Error message.
    """
    log(msg, dest=STDERR, fatal=True)


def findCygwin():
    """
    Find the path to the cygwin bin directory.  Assume it's in the path
    and has a name that contains "cygwin".  Might be "cygwin64".

    [By Bob Kline.]

    Return:
        Path to cygwin
        None if it's not in the path
    """
    for path in os.getenv("PATH").split(os.path.pathsep):
        if "cygwin" in path.lower():
            return path
    return None

def windowsPath(path):
    """
    Ensure that a file path is using Windows file separators.
    This is required if we run a Windows command and pass a filepath.
    Windows will treat the forward slash as a parameter separator.

    Pass:
        path - File path string to convert.

    Return:
        String with all forward slashes replaced.
    """
    if path:
        return path.replace("/", "\\")
    return path

def chkPath(path, isDir=False, required=False):
    """
    Check that a path points to an actual object.

    Pass:
        path     - Fully qualified file or directory name.
        isDir    - True = path must name a directory.
                   False = path must NOT name a directory.
        required - True = fatal error if not found or not isDir.

    Return:
        True     - Path found.
        False    - Not found.  If required, no return.
    """
    # Path usage message prefix
    if required:
        prefix = 'Required'
    else:
        prefix = 'Requested'

    # Path missing?
    if not path:
        if required:
            fatal("Missing a required path - internal error")
        return False

    if not os.path.exists(path):
        msg = '%s path "%s" does not exist' % (prefix, path)
        if required:
            fatal(msg)
        log(msg)
        return False

    foundDir = os.path.isdir(path)

    # Check type, directory or ordinary file
    if isDir and not foundDir:
        msg = '%s path "%s" exists but is not a directory' % (prefix, path)
        if required:
            fatal(msg)
        log(msg)
        return False
    elif not isDir and foundDir:
        msg = '%s path "%s" exists but is a directory, not ordinary file' \
               % (prefix, path)
        if required:
            fatal(msg)
        log(msg)
        return False

    # Passed all tests
    return True

def makeDirs(path, errorIsFatal=True):
    """
    Create a directory with error checking.

    Pass:
        path         - Fully qualified name of directory to create
        errorIsFatal - Fatal error if anything goes wrong.

    Return:
        True  - Success.
    """
    try:
        log('Creating directory: "%s"  errorIsFatal=%s' % (path, errorIsFatal))
        os.makedirs(path)
        chmod(path, '777')
    except Exception as e:
        if errorIsFatal:
            fatal('Unable to create directory "%s": %s' % (path, str(e)))
        return False
    return True

def chmod(dir, perms="777"):
    """
    Undo the havoc introduced by the Byzantine configuration of the CBIIT
    servers.

    No errors are recognized.  Just do what can be done and leave it at that.

    dir    - Directory on which to set permissions.
    perms  - Numeric string to pass to chmod, e.g., "777" - ignored now

    2016-12-20 - replace cygwin command with Windows ICACLS OCECDR-4125
    """

    directory = windowsPath(dir)
    for group in ("NIH\\Domain Users", "NULL SID"):
        runCmd('icacls "%s" /remove:d "%s" /T /C /Q' % (directory, group))
    runCmd('icacls "%s" /grant Everyone:(F) /T /C /Q' % directory)

def versionCtlVersion(fpath, logIt=False):
    """
    Extract the version control version number ($Id:...$) of a file,
    return it to the caller, and optionally log it.

    Failure to find the file at all is a fatal error.   Failure to
    find a version string is not an error since some files may not have
    version control keys, even if they are under version control.

    Note: No attempt is made to verify that the file content is identical to
    the content of the file in version control with the same revision
    number.  If a programmer has exported a file and then modified it,
    this function will not detect that.

    Pass:
        fpath - Path to the file, fully qualified or relative to current
                working directory.

    Return:
        Version string, or fixed message if version info not available
    """
    # Prefix identifying the source of a log message
    PREFIX = 'VERSION:'

    try:
        fp = open(fpath, 'r')
    except Exception as e:
        fatal("%s Could not open %s to find revision info: %s" %
              (PREFIX, fpath, str(e)))

    # Regex to find the version control Id key
    ID_MATCH = re.compile(r'(\$Id: ..* \$)')

    msg = None
    while msg is None:
        # Walk the file
        line = fp.readline()
        if not line:
            break

        # Search for Id string
        match = ID_MATCH.search(line)
        if match:
            msg = ("%s %s" % (PREFIX, match.group(1)))

    # If we got here, no revision info found
    if not msg:
        msg = "%s No version info found in file %s" % (PREFIX, fpath)
    if (logIt):
        log(msg)
    return msg

def availDiskGB(path):
    """
    Report how many gigabytes are available on disk.
    Code is hacked from the psutil project.
    Only works on Windows.

    Pass:
        path - Disk directory to check.  Checks the disk for the directory.

    Return:
        Integer number of gigabytes where one GB = 1,000,000,000 bytes.
        -1 if function fails.
    """
    import ctypes

    # Isolate disk to check
    path = path[:2]

    avail, total, free = ctypes.c_ulonglong(), ctypes.c_ulonglong(), \
                             ctypes.c_ulonglong()

    if sys.version_info >= (3,) or isinstance(path, unicode):
        func = ctypes.windll.kernel32.GetDiskFreeSpaceExW
    else:
        func = ctypes.windll.kernel32.GetDiskFreeSpaceExA
    rc = func(path, ctypes.byref(avail), ctypes.byref(total),
                    ctypes.byref(free))
    if rc == 0:
        return -1

    # availGB = avail.value / (1024 * 1024 * 1024)
    availGB = avail.value / (1000 * 1000 * 1000)

    return availGB

def getCdrTier():
    """
    Return the contents of the file that identifies the current tier.
    """
    global DRV
    tierFile = "%s:/etc/cdrtier.rc" % DRV

    try:
        fp = file(tierFile)
        rc = fp.read()
        tier = rc.upper().strip()
    except Exception as e:
        fatal("""
Unable to determine which tier we are on: %s
Does tier file %s exist?
""" % (str(e), tierFile))

    return tier

def evalParm(obj, parm):
    """
    Use the passed parm as the name of a field in the passed object.
    Find the value of the field.

    Pass:
        obj  - Object containing the field to evaluate.
        parm - Name of the field to evaluate, "svnurl", "svnuser", etc.

    Return:
        2-tuple of:
            Value to use, may be None, or INVALID if unrecognized.
            Value to log/display.
                This will be obscured for password fields.
    """
    # Skip any syntactic prefix, '@+', '@-'
    if parm[0] == '@':
        parm == parm[2:]

    try:
        parmVal = eval("obj.%s" % parm)
    except NameError:
        # This should have been caught earlier
        log('Internal error, invalid parameter name "%s"' % parm, STDERR)
        return (INVALID, INVALID)

    # Hardwire any password parm names in here.
    # Ugly but convenient
    if parm in ('svnpw',):
        return (parmVal, '{hidden}')

    return (parmVal, parmVal)

def delEnvKeys(keys):
    """
    Delete key from environment.  Trap and discard errors.

    Pass:
        keys - Array of names of environment variable to delete.
    """
    for key in keys:
        try:
            del os.environ[key]
        except:
            pass

def runCmd(command, obj=None, trialRun=False, failOk=False):
    """
    Run a command.

    Pass:
        command      - String form command.  See build-all.py helpcmds().
        obj          - Object containing evaluable parameters.
                       We look here to resolve '@' macros.
        trialRun     - True = Log what would be done, but don't execute.
        failOk       - True = Continue after failure, else exit.

    Return:
        Return code from executed command.  May be None.

    Notes:
        Return code is logged.  Error if non-zero is returned.

        stdout and stderr from command are captured, logged and written
        to stdout or stderr.  If anything written to stderr and failure
        is not okay, generate a fatal error.
    """
    # Nothing blocks execution yet
    allOk = True

    # Environment variables we need to clean up afterward
    envVarsSet = []

    # Unpack command and perform config substitutions
    cmdParts  = command.split()
    newParts  = []
    echoParts = []
    for part in cmdParts:

        # Special handling for pairs of (--foo/@-bar)
        if part[0] == '(':
            pair = part[1:-1].split('/')
            if not pair[1].startswith('@-'):
                log('Illegal paired construct "%s" - see --helpcmds' % part,
                     STDERR)
                allOk = False
            else:
                parmVal = obj.evalParm(pair[1])
                if parmVal[0] == INVALID:
                    # Already logged
                    allOk = False

                else:
                    # Utilize both parts of the pair or none
                    if parmVal[0] is not None:
                        newParts.append(pair[0])
                        newParts.append(parmVal[0])
                        echoParts.append(pair[0])
                        echoParts.append(parmVal[1])
                continue

        if part[0] != '@':
            # It's a literal
            newParts.append(part)
            echoParts.append(part)

        else:
            # Same handling as for pairs
            plainPart = part[2:]
            parmVal = evalParm(obj, plainPart)
            if parmVal[0] == INVALID:
                # Already logged
                allOk = False

            else:
                if parmVal[0] is None:
                    log("--%s has no value, ignoring in command" % plainPart)

                else:
                    if part[1] == '+':
                        # Set environment variable
                        if not trialRun:
                            envKey  = "CDRBUILD_%s" % plainPart.upper()
                            envVal  =  parmVal[0]
                            os.environ[envKey] = envVal
                            envVarsSet.append(envKey)
                            log("Setting env value %s=%s" % (envKey, envVal))

                    else:
                        if part[1] != '-':
                            # Macros must be @+ or @-
                            log("%s is an unrecognized command @macro" % part,
                                STDERR, False)
                            allOk = False
                        else:
                            # Substitute config value for parameter in command
                            newParts.append(parmVal[0])
                            echoParts.append(parmVal[1])

    # Put the command back together with changes
    newCmd  = " ".join(newParts)
    echoCmd = " ".join(echoParts)

    # Log sanitized command
    log("Command to execute=\n%s" % echoCmd)

    # If it's a trial run, don't do any more
    if trialRun:
        log("Command skipped for trial run")
        return 0

    output = error = None
    code   = NO_RETURN
    if allOk:
        try:
            commandStream = subprocess.Popen(newCmd, shell = True,
                                             stdin  = subprocess.PIPE,
                                             stdout = subprocess.PIPE,
                                             stderr = subprocess.PIPE)
            output, error = commandStream.communicate()
            code = commandStream.returncode

        except Exception as e:
            delEnvKeys(envVarsSet)
            # Log failure and possibly exit with fatal error
            log("Exception raised by command: %s" % str(e), STDERR, not failOk)

    delEnvKeys(envVarsSet)

    # Log info
    log("Command return code = %s" % code)
    if output:
        log("  cmd stdout\n--------------\n%s" % output)
    if error:
        log("  cmd stderr\n--------------\n%s" % error)

    # Abort on stderr output or error return code
    if code not in (0, NO_RETURN) and not failOk:
        log("Exiting after receiving return code = %s" % code, STDERR, True)
    if error and not failOk:
        log("Exiting after receiving stderr output from command", STDERR, True)

    return code
