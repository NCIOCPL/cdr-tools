# Scripts for building/deploying CDR releases

## Build
The build scripts pull source files from GitHub respositories
and transform them into packages suitable for deployment to
the CDR server.

### Requirements

The build scripts depend on having the following tools present:

 * a drive with \cdr\Bin
 * \bin\vsvars32.bat for Visual Studio 2013 on that drive
 * cygwin tools (curl, tar, etc.)
 * a connection to the internet
 * a GitHub account, with membership in the NCIOCPL organization
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
name, including case) in all of the CDR repositories (eight of them as
of this writing).

Example usage:

```build-cdr.py fermi```

## Deploy

The deployment scripts can be run directly or through
[Jenkins](https://jenkins.io/).
