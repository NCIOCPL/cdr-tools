# Scripts for building/deploying CDR releases

## Build
The build scripts pull source files from GitHub respositories
and transform them into packages suitable for deployment to
the CDR server.

### Requirements

The build scripts depend on having the following tools present:

 * a drive with \cdr\Bin
 * \bin\vsvars32.bat for Visual Studio 2013 on that drive
 * a Subversion client (GitHub supports `svn export`, but not `git archive`)
 * a connection to the internet
 * a GitHub account, with membership in the NCIOCPL organization
 * expat, Sablotron, and xerces

See https://github.com/NCIOCPL/cdr-server/blob/master/Server/README.md
for details about building the third-party libraries in that last bullet.

The deployment scripts can be run directly or through
[Jenkins](https://jenkins.io/).
