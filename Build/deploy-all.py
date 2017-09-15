#----------------------------------------------------------------
# Deploy all application program files required for the deployment
# of a patch or release to the CDR on a Windows server.
#
# The program may be run by a person using the command line, or may be
# run by the AnthillPro or other build automation software.
#
# It is intended that the source files will have been prepared by running
# build-all.py
#
# Note: No use is made of cdr specific python libraries, or functions
#       shared between
#
# BZIssue::None  (JIRA::WEBTEAM-1884)
#
#                                               Alan Meyer, May, 2014
#----------------------------------------------------------------
import sys, os, time, getopt, atexit, shutil, difflib
import BuildDeploy as bd

class GlobalVars:
    """
    Singleton class stores configuration information.
    """
    def __init__(self):
        self.diffFile      = None  # Don't deploy, just run a diff
        self.liveDrive     = 'd'   # Live CDR is found on this disk drive
        self.logfile       = None  # Logfile to be established after parms read
        self.live          = False # True=deploying to {live drive}:\cdr
        self.noErase       = False # True=don't erase target files, just update
        self.updateSchemas = True  # UpdateSchemas if ClientFiles deploy live
        self.refreshMan    = True  # RefreshManifest if ClientFiles deploy live
        self.diffArgs      = '-br' # Arguments to diff command
        self.minDisk       = 5     # Min GB free wanted on disk before start
        self.freeDisk      = 0     # GB free in target disk before start
        self.srcDir        = None  # Files to deploy found here
        self.targetDir     = None  # Deploy them to here after setting this

        # Haven't checked status of services yet
        self.cdrServiceWasRunning = False

        # Some global constants
        self.CDR_SERVICE   = 'Cdr'
        self.PUB_SERVICE   = 'cdrpublish2'
        self.SCH_SERVICE   = "CDRScheduler"

        # List of directories we visited
        self.dirsChecked = []

        # Important locations
        self.setLiveDirs()

    def setLiveDirs(self):
        """
        Set the variables naming live directories.  Called to set defaults
        and to change them if needed.
        """
        global INETPUB_DIR, WWWROOT_DIR

        # Default values of well known locations
        self.liveRoot       = '%s:\\' % self.liveDrive
        self.liveCdrDir     = os.path.join(self.liveRoot, "cdr")
        self.liveInetpubDir = os.path.join(self.liveRoot, INETPUB_DIR)
        self.liveCgiDir     = os.path.join(self.liveInetpubDir, WWWROOT_DIR)


def usage(msg=None):
    """
    Print usage message to stdout and exit.  No logging.

    Pass:
        msg - Optional error message to include
    """
    print("""
Deploy CDR release files to a live or test destination.

usage: %s {options} source_dir target_dir

 source_dir - Fully qualified location of CDR source code to deploy,
              e.g., D:\\tmp\\CdrBuild\\2014-05-06_17-43-20
              Required.
 target_dir - Fully qualified target directory name.  Files from source
              directory will be copied under this.  Files in directory A
              will be copied to target\A, etc.
              If target does not exist it will be created.
              If target exists:
                Files in all subdirectories in the source directory
                  will replace all files of the same names in the target
                  directory.
                Other files in the target directories will be erased,
                  including all subdirectories unless --noerase is
                  specified.
                Files in all other directories (i.e., not named in the
                  source directory) will be untouched.
              When --live is specified only '%s' is acceptable
              (unless --drive is also specified to change the target drive.)

Options:

 --live           Specify this when replacing a live CDR system.
                    Most directories will be copied to {drive}:\cdr\...
                    Inetpub will be copied to {drive}:\Inetpub
 --drive letter   Single drive letter (e.g. 'c', not 'c:') for where live
                    CDR is located.  Default=%s.
 --diff filename  Do not deploy files, just append a diff report to the named
                    file showing diffs between source_dir and target_dir.
                    Requires that a gnu style diff program be in the path.
 --diffargs args  Arguments to pass to diff program.  Default is '%s'.
 --noerase        Do not erase files or subdirectories prior to copying.
                    Default is to erase all files and subdirectories in a
                    target directory before copying.
 --noschemas      Do NOT update the schemas in a live deployment.  Default is
                    to install any new or modified schemas to the target
                    database if --live specified and ClientFiles built.
 --norefresh      Do NOT run RefreshManifest.py in a live deployment.  Default
                    is to run it if --live specified and ClientFiles built.
 --mindisk num    Minimum free gigabytes in target disk before allowing a run.
                    Default=%d GB
 --logfile name   Name of log file.  Default=%s
 --help           Print this display.

BEWARE:
  Deployment of ClientFiles invokes a number of CDR utilities, including
  CheckDtds, UpdateSchemas, and RefreshManifest.  Those utilities are not
  currently safe to run when deploying from an environment (like a group drive)
  that does not have a live CDR.  Bad things may happen unless and until
  this changes.  If deploying to d: from this script on L:, make a directory
  on the deployment directory (D: for most cases) the current working
  directory and invoke the script on L:, i.e.,
    D:\somwewhere> L:deploy-all.py ...
""" % (os.path.basename(sys.argv[0]), GV.liveCdrDir, GV.liveDrive,
                        GV.diffArgs, GV.minDisk, GV.logfile))
    if msg:
        sys.stderr.write("\nERROR: %s\n" % msg)
    sys.exit(1)

def serviceRunning(svcName):
    """
    Determine if a service is running.

    Note: This and other functions use the Windows "net stop" command.
    If using the "Non-Sucking Service Manager", modify this and other
    functions, and perhaps use a command line switch to switch between them.

    Pass:
        svcName - Name of the service as shown in "net start ..."

    Return:
        True  = Service is running.
        (Also logs the check.)
    """
    # Use the MS utility to check.  grep is available on all our servers
    # failOk=True to continue since grep returns non-zero = not found
    rc = bd.runCmd("net start | grep \"^ *%s$\"" % svcName, failOk=True)

    if rc:
        return False
    return True

def serviceStop(svcName):
    """
    Stop a service.  User has to have admin rights on the machine.

    Pass:
        svcName - Name of the service as shown in "net start ..."

    Return:
        True = Service successfully stopped or was not running.
    """
    if not serviceRunning(svcName):
        # Not a problem, but log it
        bd.log("Info: Request to stop non-running service: %s" % svcName)
        return True

    rc = bd.runCmd("net stop \"%s\"" % svcName, failOk=True)
    if serviceRunning(svcName):
        bd.log("Stopping service %s apparently failed, rc=%d" % (svcName, rc))
        return False

    # Wait a few seconds to be sure everything stopped
    time.sleep(5)

    return True

def serviceStart(svcName):
    """
    Start a service.  User has to have admin rights on the machine.

    Pass:
        svcName - Name of the service as shown in "net start ..."

    Return:
        True = Service successfully started.
    """
    if serviceRunning(svcName):
        bd.log("Info: Request to start already running service: %s" % svcName)
        return True

    rc = bd.runCmd("net start \"%s\"" % svcName, failOk=True)
    if not serviceRunning(svcName):
        bd.log("Starting service %s apparently failed, rc=%d" % (svcName, rc))
        return False
    return True

def postProcess():
    """
    After the main copying is done it may be necessary to:

       - Restart the cdr service (needed if client files will be post
         processed.)

       - If ClientFiles were processed:

          Invoke UpdateSchemas, if needed, to post new schemas to target.
          Build DTDs using latest schemas.
          Refresh the ClientFiles manifest to reflect any changes.

       - Restart the publishing service.

    These are done in an atexit() routine to insure that they happen when
    needed.

    Note: the ClientFiles post-processing should only run if the ClientFiles
          were deployed.
          If they do run, they require a CdrServer and the various python
          libraries and Utilities needed to interface to it.  These may not
          be available until the end of deployment.
    """
    global GV

    bd.log("Running postProcess() atexit routine")

    # Find status of the services
    cdrServiceRunning = serviceRunning(GV.CDR_SERVICE)
    pubServiceRunning = serviceRunning(GV.PUB_SERVICE)
    schServiceRunning = serviceRunning(GV.SCH_SERVICE)

    # Do we need to run client file post processing
    sawClientFiles = False
    for dir in GV.dirsChecked:
        if dir.endswith('ClientFiles'):
            sawClientFiles = True
            break

    if sawClientFiles and (GV.live or GV.diffFile) and GV.updateSchemas:

        # Post processing uses the CdrServer
        if not cdrServiceRunning:
            cdrServiceRunning = serviceStart(GV.CDR_SERVICE)

        if not cdrServiceRunning:
            bd.fatal(
            "Cdr service won't start. Could not run client file post-process")

        # ClientFiles always need the schemas, either for diff or live update
        processSchemas()

        if GV.live:
            # Do the rest only when deploying live
            checkDTDs()
            refreshManifest()

        # If we started the server just for the post procs
        if cdrServiceRunning and not GV.cdrServiceWasRunning:
            cdrServiceRunning = serviceStop(GV.cdrServiceWasRunning)

    # Restore original conditions
    if GV.cdrServiceWasRunning:
        if not cdrServiceRunning:
            serviceStart(GV.CDR_SERVICE)
        if not pubServiceRunning:
            serviceStart(GV.PUB_SERVICE)
    if GV.schServiceWasRunning:
        if not schServiceRunning:
            serviceStart(GV.SCH_SERVICE)


def processSchemas():
    """
    Examine all of the schemas from the version control archive and compare
    them to what's in the current tier's database document table.

    Output information about the comparison - was each schema in version
    control found in the database, and was it identical (after normalization)
    to the copy in the version archive?

    If running in live mode:

       Update any schemas in the database to match copies that differ in
       version control.

       Add any schemes to the database that are in version control but not
       in the database.

    Return:
        Count of schemas updated.
    """
    global GV

    checkedCount = 0
    newCount     = 0
    changedCount = 0
    updatedCount = 0

    # Schemas from version control were copied into the Schemas directory
    #  built by copyAll()
    # If it doesn't exist, we don't process schemas.  There's nothing to do.
    bd.log("DEBUG: processSchemas, GV.srcDir=%s" % GV.srcDir)
    schemaDir = os.path.join(GV.targetDir, 'Schemas')
    if not bd.chkPath(schemaDir, isDir=True):
        bd.log("Schemas not built by build-all.py.  Updates not checked.")
        return updatedCount

    # Processing either a diff or a deployment, nothing else looks at schemas
    if not GV.diffFile and not GV.live:
        bd.log("Not doing a diff or live update.  Schema updates not wanted.")
        return updatedCount

    bd.log("Running processSchemas()")

    # Put in a banner / separator
    diffFp = None
    if GV.diffFile is not None:
        try:
            diffFp = open(GV.diffFile, "a")
            diffFp.write("""
=====================================================================
        CDR deploy-all schema diff report: %s
=====================================================================
""" % time.ctime())
        except Exception as e:
            bd.fatal("Unable to open diff file %s 2nd time for append: %s" %
                      (GV.diffFile, str(e)))

    # UpdateSchema constants
    SCHEMA_PRG = "%s:/cdr/bin/UpdateSchemas.py" % GV.liveDrive
    SCHEMA_UID = 'SchemaUpdater'
    SCHEMA_PWD = os.environ.get("SCHEMA_PWD") # PROVIDED THROUGH JENKINS
    SCHEMA_CMD = '%s %s %s' % (SCHEMA_PRG, SCHEMA_UID, SCHEMA_PWD)

    # This function requires lib/Python.  It will be available if deploying to
    # an existing CDR installation or new one for which lib/Python is deployed.
    start = os.getcwd()
    try:
        os.chdir(GV.liveRoot)
        import cdr
    except ImportError as e:
        os.chdir(start)
        bd.log('ERROR: Unable to import: "%s" - processSchemas() not run' % e)
        return

    # Differencing object
    differ = difflib.Differ()

    # For each schema in the directory, get and compare to target database
    os.chdir(schemaDir)
    for schemaName in os.listdir("."):
        # There's currently a file in this version control directory
        #  that's not a schema.  Skip it.
        if not schemaName.endswith('.xml'):
            continue

        query = "CdrCtl/Title='%s' and CdrCtl/DocType='schema'" % schemaName
        results = cdr.search('guest', query)
        checkedCount += 1
        if len(results) < 1:
            # Report
            newCount += 1
            if diffFp:
                diffFp.write("Schema '%s' - Only in version control.\n" %
                              schemaName)
            else:
                # Add the new schema to the database
                # XXX Add capability to obscure uid/pw in the log?
                fname = bd.windowsPath(schemaName)
                cmd = '%s %s' % (SCHEMA_CMD, fname)
                changedCount += 1
                bd.runCmd(cmd)
                # bd.runCmd(cmd, trialRun=True)
            continue

        # Should never be more than one
        if len(results) > 1:
            bd.fatal("Found more than one schema named '%s' - can't happen"
                      % schemaName)

        # Get newly exported schema
        schemaFile = os.path.join(schemaDir, schemaName)
        fp = open(schemaFile)
        newXml = fp.read().splitlines()
        fp.close()

        # Get existing schema from the target database
        # Restoring final newline stripped from oldXml when stored in db
        docId  = cdr.exNormalize(results[0].docId)[1]
        doc    = cdr.getDoc('guest', docId, getObject=True)
        oldXml = doc.xml.splitlines()

        # Delete trailing blank lines
        while oldXml[-1:] == "\n":
            oldXml = oldXml[:-1]

        # Compare them, line by line
        result = differ.compare(oldXml, newXml)

        # Extract the results
        diff = []
        for line in result:
            # Only want lines that are different
            # Discard beginning ' ' = Lines are the same
            # Discard beginning '?' = Character highlighter line
            if line[0] not in (' ', '?'):
                diff.append(line)

        # No changes?
        if len(diff) == 1:
            # Schema docs in the database have an extra line at the end
            # We don't know why, but it's not a significant difference
            # See comment in DevTools/Utilities/DiffSchemas.py
            continue

        # If we're running a diff, report the results
        changedCount += 1
        if diffFp:
            output = "\n".join(diff)
            diffFp.write("Schema '%s': -from database  +from version control\n"
                          % schemaName)
            diffFp.write(output)
        else:
            # Schema is different in version control and DB.  Update DB.
            cmd = '%s %s' % (SCHEMA_CMD, schemaName)
            updatedCount += 1
            bd.runCmd(cmd)
            # bd.runCmd(cmd, trialRun=True)

    # Back to whereever we were running from
    os.chdir(start)

    if diffFp:
        try:
            diffFp.write("""
  %3d schemas found in version control
  %3d schemas only in version control
  %3d schemas different between version control and database
  %3d schemas inserted or updated in database

=====================================================================
        End schema diff report: %s
=====================================================================
""" % (checkedCount, newCount, changedCount, updatedCount, time.ctime()))
            diffFp.close()
        except Exception as e:
            bd.fatal("Unable to finalize schema diff %s: %s" %
                      (GV.diffFile, str(e)))

    bd.log("Checked %d schemas, updated %d" % (checkedCount, updatedCount))
    return updatedCount

def checkDTDs():
    """
    Generate DTDs from the latest schemas on the target server.

    Done if/when ClientFiles and (possibly) schemas are updated.

    Do it AFTER processSchemas() and BEFORE refreshManifest()
    """
    global GV, SCRIPT_DIR

    # Schemas already updated in the database.
    # DTDs already established in the live ClientFiles directory.
    # Check and update DTDs against Schemas
    # Results written to, and captured from, stdout
    bd.log("Checking and, if necessary, regenerating DTDs")

    # CheckDtds assumes we are on target drive
    # XXX May want to modify cdrutil.py, but problem may be deeper than that
    ckDtds = os.path.join(SCRIPT_DIR, "CheckDtds.py")
    ckDtds = bd.windowsPath(ckDtds)
    start = os.getcwd()
    os.chdir(GV.liveRoot)
    bd.runCmd("python %s" % ckDtds)
    os.chdir(start)

def refreshManifest():
    """
    Refresh the ClientFiles manifest sent to the client computer.  See
    RefreshManifest.py for information on what that does.

    This needs to be done if:
        Client files were updated in the live directory.
        --norefresh was NOT specified as an argument to the program.

    It uses RefreshManifest.py, which imports cdr.py, which might not
    be present or up to date at the time the client files were updated.
    Therefore we wait until everything is done before calling this.
    """
    global GV, SCRIPT_DIR

    if not GV.refreshMan:
        bd.log('--norefresh specified, manifest not refreshed')
        return

    if not GV.live:
        bd.log('--live not specified, manifest not refreshed')
        return

    # RefreshManifest should be in the same directory as this script
    refreshMan = os.path.join(SCRIPT_DIR, "RefreshManifest.py")
    bd.log("Running %s" % refreshMan)

    # But it has to run on the live drive to find the apphost file
    start = os.getcwd()
    os.chdir(GV.liveRoot)
    bd.runCmd("python %s" % refreshMan)
    os.chdir(start)
    bd.log("RefreshManifest complete")

def diffSrcTarget():
    """
    Diff the source and target directories using a GNU style diff program
    required to be in the current path.
    """
    global GV

    # Put in a banner / separator
    try:
        fp = open(GV.diffFile, "a")
        fp.write("""
=====================================================================
        CDR deploy-all diff report: %s
=====================================================================
""" % time.ctime())
        fp.close()
    except Exception as e:
        bd.fatal("Unable to open diff file %s for append: %s" %
                  (GV.diffFile, str(e)))

    # Diff each directory separately
    for path, dirs, files in os.walk(GV.srcDir):
        for dir in dirs:
            srcDir = os.path.join(path, dir)
            if dir == 'Schemas':
                # These are handled later, comparing with db, not files
                continue
            if dir == 'Inetpub':
                targDir = GV.liveInetpubDir
            else:
                targDir = os.path.join(GV.liveCdrDir, dir)

            # Run the diff.  failOk to continue after diff returns non-zero
            bd.runCmd("diff %s %s %s >> %s" %
                     (GV.diffArgs, targDir, srcDir, GV.diffFile), failOk=True)

        # Only processing the top level, diff handles the recursion
        break

    try:
        fp = open(GV.diffFile, "a")
        fp.write("""
=====================================================================
        End diff report: %s
=====================================================================
""" % time.ctime())
        fp.close()
    except Exception as e:
        bd.fatal("Unable to finalize diff report %s: %s" %
                  (GV.diffFile, str(e)))

    bd.log("See diff output file in %s" % GV.diffFile)
    exit(0)

def checkTargets():
    """
    Perform a sanity check to be sure that any targets either don't exist
    or are directories, not ordinary files.

    This should never fail.
    """
    global GV

    for path, dirs, files in os.walk(GV.srcDir):
        for dir in dirs:
            if dir not in ('Inetpub', 'wwwroot'):
                targetPath = os.path.join(GV.targetDir, dir)
                if os.path.exists(targetPath):
                    if not os.path.isdir(targetPath):
                        bd.fatal(
                          "Target path '%s' exists but is not a directory" %
                          targetPath)

        # Only checking the top level
        break

def copyOrdinaryFiles(srcDir, targetDir):
    """
    Copy ordinary files, not directories, from the source to the target
    directory.

    Not recursive.

    Pass:
        srcDir    - copy from here.
        targetDir - to here.
    """
    global GV

    for fname in os.listdir(srcDir):
        srcFile    = os.path.join(srcDir, fname)
        targetFile = os.path.join(targetDir, fname)
        if not os.path.isdir(srcFile):
            # Using a method that should work in Windows
            bd.log("  Copying '%s'" % targetFile)
            shutil.copy(srcFile, targetFile)

    # If we copied client files into a live directory, schedule a
    # ClientFiles RefreshManifest unless otherwise directed
    if targetDir.endswith("\ClientFiles") and (GV.live or GV.diffFile):
        GV.liveClientFiles = True

def usesLiveCGI(path, dir):
    """
    Determine if a directory to be deployed is going to the live CGI tree
    or to some other place in the output - either a non-live location, or
    a live location in the \cdr tree, not the Inetpub tree.

    Pass:
        path - Path in the source tree to be copied.
               The first element of the triple returned by os.path.walk().
        dir  - Directory in the source tree to be copied.
               An element of the array returned as the second element by
               os.path.walk().

    Return:
        True = Yes, this should be routed to the live CGI directory tree.
    """
    global GV, INETPUB_DIR, WWWROOT_DIR

    # No issue if we're not running --live, or if we've already done this
    if not GV.live:
        return False

    # Isolate the part of the input directory that is really output
    pastBase   = len(GV.srcDir) + 1
    outputPath = path[pastBase:]

    # Look for the website path heads
    if (
          ( outputPath.startswith(INETPUB_DIR) or
            outputPath.startswith(WWWROOT_DIR) )
        or
          ( outputPath == '' and dir in (INETPUB_DIR, WWWROOT_DIR) )
       ):
        return True

    return False

def copyCgiFiles():
    """
    Special handling of CGI files in a live deployment.
    They don't go to the main target directory - \cdr.

    This function starts at the top of the source tree for the CGI
    files and copies all of them.  It only needs to be called once.
    """
    global INETPUB_DIR, WWWROOT_DIR

    # Insurance check: this is a copy to the live directory
    if not GV.live:
        bd.fatal("Internal error, copyCgiFiles called for non-live deployment")

    # DEBUG
    # sys.exit(1)

    # Check live site, these directories should already exist
    if not os.path.exists(GV.liveCgiDir):
        bd.fatal("CGI directory root '%s' does not exist.  Can't happen!")

    # Check sources, looking for Inetpub\wwwroot or just \wwwroot
    srcDir = os.path.join(GV.srcDir, INETPUB_DIR, WWWROOT_DIR)
    if not os.path.exists(srcDir):
        srcDir = os.path.join(GV.srcDir, WWWROOT_DIR)
        if not os.path.exists(srcDir):
            bd.fatal("Cannot find source directory for CGI files")

    # There can be other things besides CDR in Inetpub, use caution
    cdrCgiDirs = (os.path.join(GV.liveCgiDir, "cgi-bin"),
                  os.path.join(GV.liveCgiDir, "images"),
                  os.path.join(GV.liveCgiDir, "js"),
                  os.path.join(GV.liveCgiDir, "stylesheets")
                 )

    # Set permissions to ensure we can delete or overwrite
    bd.chmod(GV.liveCgiDir)

    if not GV.noErase:
        # Delete the directories
        bd.log("Deleting data from live CGI directories")
        for dir in cdrCgiDirs:
            if os.path.exists(dir):
                dir = bd.windowsPath(dir)
                bd.log("Recursively deleting directory: %s" % dir)
                bd.runCmd("RMDIR /Q /S %s" % dir)

    # Copy
    bd.log("copying wwwroot files")
    bd.runCmd("XCOPY /E /R /Y %s\\* %s" %
              (bd.windowsPath(srcDir), bd.windowsPath(GV.liveCgiDir)))

    start = os.getcwd()
    os.chdir(GV.liveCgiDir)

    # Select the proper favicon for this tier
    bd.log("Setting favicon.ico for tier %s" % TIER)

    # XXX There is a mismatch between wanted "favicon-qa.ico" name
    #     and svn named "favicon-test.ico"
    faviconTier = TIER.lower()
    if faviconTier == 'qa':
        faviconTier = 'test'
    shutil.copy("favicon-%s.ico" % faviconTier, "favicon.ico")

    # Set permissions as well as we can.  See comments in copyAll()
    bd.chmod(GV.liveCgiDir)
    os.chdir(start)

def copyAll():
    """
    Copy all of the files in the source directories to corresponding
    target directories or elsewhere in the special case of a live Inetpub
    deployment.
    """
    global GV

    # Make sure permissions on the source tree are OK.
    bd.chmod(GV.srcDir)

    # True = I've updated the CGI directories already
    ranLiveCGI = False

    # Register post-processing to do after copies
    bd.log("Registering postProcess() atexit routine")
    atexit.register(postProcess)

    # If the target is a live system we need to stop CDR services before
    #  swapping in new software
    if GV.live:
        # Stop them in the proper order
        if GV.schServiceWasRunning:
            serviceStop(GV.SCH_SERVICE)
        else:
            bd.log("scheduler service was not running; will not be started")
        # Only do this if the services weren't stopped outside of this
        #  progrmam.  If the user did it himself, he may have a reason
        #  for keeping things off.
        if GV.cdrServiceWasRunning:

            serviceStop(GV.PUB_SERVICE)
            serviceStop(GV.CDR_SERVICE)
        else:
            bd.log("""
Notice: The Cdr service does not appear to be running.
This script will therefore not automatically restart it.
Don't forget to restart the services (%s and %s) when work is
complete.
""" % (GV.CDR_SERVICE, GV.PUB_SERVICE))

    # Handle deletions at the top level only, they're recursive
    topLevel = True

    # Walk the source directory tree
    for path, dirs, files in os.walk(GV.srcDir):
        bd.log("Path %s: dirs=%s" % (path, dirs))
        for dir in dirs:
            GV.dirsChecked.append("%s\\%s" % (path, dir))

            # Special handling for files not destined for the \cdr directory
            # The live CGI directory is special and this gives maximum
            #   flexibility for treating it specially
            if usesLiveCGI(path, dir):
                # Only run it once.  Entire subtree will be processed
                if not ranLiveCGI:
                    copyCgiFiles()
                    ranLiveCGI = True

            else:
                # Full path to the target directory for each source directory
                #  target directory + part of source path after the top level
                #  source directory + directory found by the walk
                targetDir = os.path.join(GV.targetDir,
                                         path[len(GV.srcDir)+1:], dir)

                # May need to remove top level target directories and all
                #  sub-directories beneath them
                if topLevel:
                    if not GV.noErase:
                        if os.path.exists(targetDir):
                            bd.log("Deleting tree '%s'" % targetDir)
                            bd.chmod(targetDir, "777")
                            shutil.rmtree(targetDir)

                # Create the directory if needed
                if not os.path.exists(targetDir):
                    bd.makeDirs(targetDir)

                # Copy all of the files in the source dir
                srcDir = os.path.join(path, dir)
                copyOrdinaryFiles(srcDir, targetDir)

                bd.log("Setting permissions on exported files in %s" %
                        targetDir)
                bd.chmod(targetDir, "777")

        # Below the top level all dirs to delete are already gone
        topLevel = False

def reportExamined(examList):
    """
    Log the list of directories examined.

    Pass:
        examList - the list of directories.
    """
    examined = []
    examined.append("\nDirectories examined:")
    for dir in examList:
        examined.append("   %s" % dir)
    examinedStr = "\n".join(examined)
    examinedStr += "\n"

    bd.log(examinedStr)

def checkPrerequisites():
    """
    Check that all prerquisites for a successful run that can be checked
    are okay.

    Log errors and keep going, but abort processing at end if any fatal
    errors were detected.
    """
    global GV, TIER

    fatalError = False

    # If we can't find the tier exception is raised
    TIER = bd.getCdrTier()

    # Disk drive for live directory must exist
    liveRoot = os.path.join(GV.liveDrive, "/")
    if not bd.chkPath(liveRoot, True):
        bd.log("The --live disk drive (%s) cannot be found" % GV.liveDrive)
        fatalError = True

    # Make comparable path strings
    winTargDir = bd.windowsPath(GV.targetDir)
    winLiveDir = bd.windowsPath(GV.liveCdrDir)

    # The live directory is non-negotiable
    if GV.live:
        if winTargDir and winTargDir != winLiveDir:
            bd.log("targ=%s  live=%s'" % (GV.targetDir, GV.liveCdrDir))
            bd.log("The only valid live directory is '%s'" % GV.liveCdrDir)
            fatalError = True
        GV.targetDir = GV.liveCdrDir

    else:
        # If writing to the live directory, must specify --live
        # But if we're just doing a diff, the live directory is okay
        if winTargDir == winLiveDir and not GV.diffFile:
            bd.log("Must specify --live to write to the CDR directory")
            fatalError = True

    # Required parms okay?
    if not bd.chkPath(GV.srcDir, True):
        bd.log("Source directory is not found")
        fatalError = True

    # Must have access to cygwin chmod
    if not bd.findCygwin():
        bd.log("Could not find required cygwin directory in the PATH")
        fatalError = True

    # Don't proceed unless we have a reasonable amount of disk
    GV.freeDisk = bd.availDiskGB(GV.targetDir)
    if GV.freeDisk < 0:
        bd.log("Warning: Unable to determine free disk space at %s" %
             GV.targetDir, bd.STDERR)
    else:
        if GV.freeDisk < GV.minDisk:
            bd.log("%d GB disk space < than minimum %d GB specified" %
                     (GV.freeDisk, GV.minDisk))
            fatalError = True

    # Any fatal errors require abort
    if fatalError:
        bd.fatal("Aborting after fatal error(s)")

# ---------------------------------------------------------------------
#                      MAIN
# ---------------------------------------------------------------------
# Constants
INETPUB_DIR = "Inetpub"
WWWROOT_DIR = "wwwroot"
SCRIPT_DIR  = os.path.dirname(sys.argv[0])

# Establish global configuration parameters with defaults
GV = GlobalVars()

# Globals.  Some are overridden due to command line parameters
# Note: os.path.join won't handle drive letters at the root unless we say to

# Provisionally set logfile name.  It may change later if options change it
# Get parameters
longOpts = ("live", "diff=", "drive=", "noerase", "logfile=", 'diffargs=',
            "mindisk=", "noschemas", "norefresh", "help")
try:
    (opts, args) = getopt.getopt(sys.argv[1:], "", longOpts)
except getopt.GetoptError as e:
    usage(str(e))

# Options
for opt, arg in opts:
    if opt == "--live":
        GV.live = True

    if opt == "--diff":
        GV.diffFile = arg

    if opt == "--drive":
        GV.liveDrive = arg
        GV.liveRoot  = "%s:/" % GV.liveDrive
        # Set it for the BuildDeploy module as well
        bd.setDrive(GV.liveDrive)

    if opt == "--noerase":
        GV.noErase = True

    if opt == "--noschemas":
        GV.updateSchemas = False

    if opt == "--norefresh":
        GV.refreshMan = False

    if opt == "--logfile":
        GV.logfile = arg

    if opt == "--diffargs":
        GV.diffArgs = arg

    if opt == "--mindisk":
        GV.minDisk = int(arg)

    if opt == "--help":
        usage()

# Fixed args
if len(args) < 2:
    usage("Source and target directory names are required")
if len(args) > 2:
    usage("Extra argument(s) on command line")
GV.srcDir    = args[0]
GV.targetDir = args[1]


# Set the log file name after possible --drive and --logfile parsed
# but before any possible bd.log() or bd.fatal() calls
if not GV.logfile:
    GV.logfile = "%s:\\cdr\\log\\deploy.log" % GV.liveDrive
bd.setLogfileName(GV.logfile)

# Update some directory paths in case GV.liveDrive changed
GV.setLiveDirs()

# Tier will be set when we check prerequisites
TIER = None

# Remember whether the CDR service was running at the outset
GV.cdrServiceWasRunning = serviceRunning(GV.CDR_SERVICE)

# Same for the scheduler service
GV.schServiceWasRunning = serviceRunning(GV.SCH_SERVICE)

# Are all prerequisites satisfied?
checkPrerequisites()

# Initialize logging - we don't write all of this to the log until
#  the parms are good enough to have passed checkPrerequisites().
bd.log("""
=====================================================================
                         Deploying CDR
=====================================================================

%s

Deployment parameters:

 source_dir:   %s
 target_dir:   %s

  --diffFile:  %s
  --drive:     %s
  --live:      %s
  --noerase:   %s
  --noschemas: %s
  --norefresh: %s
  --logfile:   %s
  --mindisk:   %d
  free disk:   %d
 found tier:   %s

""" % (bd.versionCtlVersion(sys.argv[0]),
       GV.srcDir, GV.targetDir, GV.diffFile, GV.liveDrive,
       GV.live, GV.noErase, not GV.updateSchemas, not GV.refreshMan,
       GV.logfile, GV.minDisk, GV.freeDisk, TIER))

# If a diff is requested, do it
if GV.diffFile:
    diffSrcTarget()

else:
    # Check that targets don't exist or are directories
    checkTargets()

    # Copy everything
    bd.log("COPYING ALL FILES")
    copyAll()

# Report the list of directories examined
reportExamined(GV.dirsChecked)

bd.log("""
=====================================================================
                         Deployment Complete
=====================================================================
""")
