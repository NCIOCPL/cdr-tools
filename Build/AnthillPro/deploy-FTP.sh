#!/bin/bash
#----------------------------------------------------------------------
# Install a new release of software for the FTP server.
# Copied to /cdr_deployments/$RELEASE/linux/FTP as deploy.sh
# and invoked by /cdr/deployments/$RELEASE/glossifier.sh (the
# ftp server is the same host as the glossifier server). The
# glossifier.sh script is run by CBIIT on the upper tiers, to
# which the developers have no access.
#----------------------------------------------------------------------

echo "======= Begin deployment of FTP files ======"
hostname; date

#----------------------------------------------------------------------
# Caller must tell us where the files are.
#----------------------------------------------------------------------
SRC_DIR=$1
if [ -z "$SRC_DIR" ]
then
    echo "usage: $0 SOURCE-DIRECTORY"
    exit 1
fi
if [ ! -r "$SRC_DIR/prod/docs/pdq.dtd" ]
then
    echo "$SRC_DIR is not a source directory for the FTP server"
    exit
fi

#----------------------------------------------------------------------
# Set up the rest of our variables. Avoid leading slashes for tar
# but put them in right after invoking tar.
#----------------------------------------------------------------------
NOW=`date "+%Y%m%d_%H%M%S"`
CDROPERATOR_HOME=home/cdroperator
BACKUP=/$CDROPERATOR_HOME/temp/cdrftp_backup_$NOW.tar.bz2
PROD=$CDROPERATOR_HOME/prod
FTPROOT=u/ftp/cdr/pub/pdq
DOCS=$FTPROOT/docs
FULL=$FTPROOT/full
PBIN=$PROD/bin
PLIB=$PROD/lib
PDOC=$PROD/docs
PYMODULES=usr/local/cdr/lib/Python
SUDO=/usr/bin/sudo
BACK_ME_UP="$PBIN $PLIB $PDOC $PYMODULES $DOCS"

#----------------------------------------------------------------------
# Back up the old files.
#----------------------------------------------------------------------
echo -n "backing up old files to $BACKUP..."
$SUDO -u cdroperator /bin/tar -cjf $BACKUP -C / $BACK_ME_UP
echo "done"

#----------------------------------------------------------------------
# Fix the paths which need leading slashes, now that we don't have to
# worry about tar's warning message about stripping them.
#----------------------------------------------------------------------
PBIN=/$PBIN
PLIB=/$PLIB
PDOC=/$PDOC
PYMODULES=/$PYMODULES
DOCS=/$DOCS
FULL=/$FULL

#----------------------------------------------------------------------
# Clear out old versions.
#----------------------------------------------------------------------
echo -n "clearing out old versions of files..."
$SUDO -u cdroperator /bin/rm -rf $PYMODULES/* $PBIN/* $PLIB/* $PDOC/* $DOCS/*
echo "done"

#----------------------------------------------------------------------
# Replace with the new sets.
#----------------------------------------------------------------------
echo -n "installing new files..."
$SUDO -u cdroperator /bin/cp -f $SRC_DIR/prod/bin/* $PBIN
$SUDO -u cdroperator /bin/cp -f $SRC_DIR/prod/lib/* $PLIB
$SUDO -u cdroperator /bin/cp -f $SRC_DIR/prod/docs/* $PDOC
$SUDO -u cdroperator /bin/cp -f $SRC_DIR/Python/* $PYMODULES
$SUDO -u cdroperator /bin/cp -f $SRC_DIR/prod/docs/* $DOCS
echo "done"

#----------------------------------------------------------------------
# List the files in the locations of interest.
#----------------------------------------------------------------------
echo -e "\nCHECK PERMISSIONS IN THE FOLLOWING DIRECTORIES"
echo $PBIN;      $SUDO -u cdroperator ls -l $PBIN;      echo
echo $PLIB;      $SUDO -u cdroperator ls -l $PLIB;      echo
echo $PDOC;      $SUDO -u cdroperator ls -l $PDOC;      echo
echo $FULL;      $SUDO -u cdroperator ls -l $FULL;      echo
echo $PYMODULES; $SUDO -u cdroperator ls -l $PYMODULES; echo
echo "======= Finished deployment of FTP files ======"
