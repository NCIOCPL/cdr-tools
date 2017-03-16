#!/bin/bash
#----------------------------------------------------------------------
# Install a new release of software for the Emailer server.
# Copied to /cdr_deployments/$RELEASE/linux/Emailers/deploy.sh
# and invoked by /cdr/deployments/$RELEASE/emailer.sh (run by
# CBIIT on the upper tiers).
#----------------------------------------------------------------------

echo "======= Begin deployment of Emailer files ======"
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
if [ ! -r "$SRC_DIR/cgi-bin/cgsd.py" ]
then
    echo "$SRC_DIR is not a source directory for the Emailer server"
    exit 1
fi

#----------------------------------------------------------------------
# Set up the rest of our variables. Avoid leading slashes for tar
# but put them in right after invoking tar.
#----------------------------------------------------------------------
NOW=`date "+%Y%m%d_%H%M%S"`
CGI_BIN=web/gpmailers/cgi-bin
IMAGES=web/gpmailers/wwwroot/images
EMAILERS_HOME=home/emailers
BIN=$EMAILERS_HOME/bin
EMAILERS_BACKUP=/$EMAILERS_HOME/backup
BACKUP=$EMAILERS_BACKUP/emailers_backup_$NOW.tar.bz2
PYMODULES=usr/local/cdr/lib/Python
SUDO=/usr/bin/sudo
LOGDIR=/usr/local/cdr/log

#----------------------------------------------------------------------
# Back up the old files.
#----------------------------------------------------------------------
if [ ! -d $EMAILERS_BACKUP ]
then
    echo -n "creating $EMAILERS_BACKUP..."
    $SUDO -u emailers /bin/mkdir $EMAILERS_BACKUP
    echo "done"
fi
echo -n "backing up old files to $BACKUP..."
$SUDO -u emailers /bin/tar -cjf $BACKUP -C / $CGI_BIN $BIN $IMAGES $PYMODULES
echo "done"

#----------------------------------------------------------------------
# Fix the paths which need leading slashes, now that we don't have to
# worry about tar's warning message about stripping them.
#----------------------------------------------------------------------
CGI_BIN=/$CGI_BIN
IMAGES=/$IMAGES
BIN=/$BIN
PYMODULES=/$PYMODULES

#----------------------------------------------------------------------
# Clear out old versions.
#----------------------------------------------------------------------
echo -n "clearing out old versions of files..."
$SUDO -u emailers /bin/rm -rf $CGI_BIN/* $BIN/* $IMAGES/*
$SUDO -u cdroperator /bin/rm -rf $PYMODULES/*
echo "done"

#----------------------------------------------------------------------
# Replace with the new sets.
#----------------------------------------------------------------------
echo -n "installing new files..."
$SUDO -u emailers /bin/cp -f $SRC_DIR/cgi-bin/* $CGI_BIN
$SUDO -u emailers /bin/cp -f $SRC_DIR/images/* $IMAGES
$SUDO -u emailers /bin/cp -f $SRC_DIR/util/LoadGPEmailers $BIN
$SUDO -u cdroperator /bin/cp -f $SRC_DIR/Python/* $PYMODULES
echo "done"

#----------------------------------------------------------------------
# List the files in the locations of interest.
#----------------------------------------------------------------------
echo -e "\nCHECK PERMISSIONS IN THE FOLLOWING DIRECTORIES"
echo $CGI_BIN;   $SUDO -u emailers    ls -l $CGI_BIN;   echo
echo $BIN;       $SUDO -u emailers    ls -l $BIN;       echo
echo $IMAGES;    $SUDO -u emailers    ls -l $IMAGES;    echo
echo $PYMODULES; $SUDO -u cdroperator ls -l $PYMODULES; echo
echo $LOGDIR;    $SUDO -u cdroperator ls -l $LOGDIR;    echo
echo "======= Finished deployment of Emailer files ======"
