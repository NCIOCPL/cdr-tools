# Scripts for building/deploying CDR releases

## Build
The build scripts pull source files from GitHub respositories
and transform them into packages suitable for deployment to
the CDR server.

### Requirements

The build scripts depend on having the following tools present:

 * a drive with `\cdr\Bin`
 * `\VisualStudio\VC\Auxiliary\Build\vcvars64.bat` for Visual Studio 2019
    on that drive
 * cygwin tools (`curl`, `tar`, _etc._)
 * a connection to the internet
 * a branch in each of the repositories from which the build will pull code

### Usage

While it is possible to run the separate batch files for the individual
portions of a CDR build, the simplest way to create a complete or partial
build is to run `build-cdr.py` with the appropriate command-line arguments.
The script has one required argument naming the branch from which the build
is to be created. For details on the available options, invoke the script
with the `--help` option:

```build-cdr.py --help```

It is necessary, as noted above, that the branch named on the command line
be present in all of the CDR repositories from which code will be pulled.
It is possible to do a partial build with the branch created in only one
or two of the repositories, but it is generally more straightforward if
when work on a new release is begun the branch is created (with the same
name, including case) in all of the CDR repositories (seven of them as
of this writing).

Example usage:

```build-cdr.py oersted```

All of the build tools log their processing activity in `d:/cdr/logs/build.log`.

## Check

The build script will have created a deployment set under `d:/tmp/builds`
(unless the location has been overridden on the command line). For example:

```
d:/tmp/builds/oersted-20220224095047
```

In many cases it will be useful to compare the build set with the live development
server. This step can reveal the existence of code which has been implemented and
tested on that server, but has not been checked into the branch. To perform such a
check, run the `check-build.py` script. For example,

```
check-build.py d:\tmp\builds\oersted-20220224095047 > d:\tmp\oersted.diff
```

To see all of the supported command-line options, run

```
check-build.py --help
```

For example, if the development team have not consistently used universal line endings
for the code, it may be necessary to use the `-w` option to ignore whitespace differences.

After the command has produced its report of the differences between the live server and
the release deployment set, examine that report to identify changes which have failed to
be included in the branch for the release.

This step will not be as helpful when more than one release is under development at the
same time, as the CDR project does not have the luxury of separate development servers
for each concurrent release.

## Deployment to QA

Copy the deployment set to the shared directory for CDR deployments. It is usually convenient
to map a drive letter (`U:` will be used in the examples for this document) for the share.
For example:

```
net use U: [UNC path to network share, omitted from this document]
cd /D d:\tmp\builds
xcopy /S /I oersted-20220224095047 U:\oersted
```

When the `xcopy` command asks if the target (in this example, "oersted") is a directory
or a file, respond with `D` to indicate that it is a directory.
If you are replacing an existing deployment set at the same location, be sure to clear out subdirectories and files from the previous deployment set first.

Make sure the file permissions survived the copy by running the
`D:\cdr\bin\fix-permissions.cmd` script on the build set directory. This may take a
minute or two to complete. For example:

```
D:\cdr\bin\fix-permissions.cmd U:\oersted
```

Copy the `install.bat` template from the repository's `tools/Build` directory
and modify it as necessary for the current release. The minimum modification
required is to find the "REPLACEME" string and substitute the name of the directory
(in this example, `\\[server-name]\cdr-deployments\oersted`) where the deployment set
is located on the `cdr_deployments` share described above. Use the UNC path for the
directory so that the script is not dependent on your own drive mapping.
Put the copied/modified script in that directory.

You may also need to add any extra steps which are needed for the deployment, but
not performed by the standard deployment script. For example, you may need to
run a separate Python script to create and/or populate a database table for
a new requirement supported by the release.

Make sure that none of the members of the development team have any open editing
or viewing processes for files in any of the code or client directories on the CDR
QA server which would prevent clearing out files from the previous release.
Log into the CDR QA server with your alternate ("aa") NIH domain account and open
a console command window using the _Open as Administrator_ option. From that console
window run the `install.bat` script described above. You may need to use the UNC path
for the script's location if the share's drive mapping is for your primary domain account.
For example:

```
\\server-name\cdr-deployments\oersted\install.bat
```

After the deployment script has reported successful completion you can press any
key to end the process, and perform any manual steps required for the release
(for example, create and enable any new scheduled jobs).

## Deployment to CDR STAGE

If the users find any new bugs during the user acceptance testing of the final
iteration on QA, the bugs must be fixed and a new build must be created, deployed
and re-tested. Lather, rinse, repeat. Once the users have determined that there
are no bugs in the final build for the release, CBIIT needs to deploy the release
to the CDR STAGE server. Open a ServiceNow ticket requesting that CBIIT run the
`install.bat` script on the `cdr_deployments` share for the release.

Once the release has been deployed to the CDR STAGE server, a second ServiceNow
ticket can be submitted for the release to get a security scan.

## Deployment to CDR Production

It is generally not necessary to wait for the security scan to complete before
requesting that CBIIT deploy the release to the production tier. The users are
generally given the opportunity to spot check the release on CDR STAGE, but it
is expected that any problems would have been identified during the testing of
the release on the CDR QA server. Unlike the STAGE deployment, the production
deployment's timing needs to be coordinated with the users and scheduled so that
the downtime for the deployment happens outside normal business hours. As with
the lower tiers, be sure to take care of any extra manual tasks (_e.g._, creation
of new user groups or permissions).
