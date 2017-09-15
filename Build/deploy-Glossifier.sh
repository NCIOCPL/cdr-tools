#!/bin/bash
#----------------------------------------------------------------------
# Install a new release of software for the Glossifier server.
# Copied to /cdr_deployments/$RELEASE/linux/Glossifier/deploy.sh
# and invoked by /cdr/deployments/$RELEASE/glossifier.sh (run by
# CBIIT on the upper tiers).
#----------------------------------------------------------------------

echo "======= Begin deployment of Glossifier files ======"
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
if [ ! -r "$SRC_DIR/cgi-bin/glossify" ]
then
    echo "$SRC_DIR is not a source directory for the Glossifier server"
    exit
fi

#----------------------------------------------------------------------
# Set up the rest of our variables. Avoid leading slashes for tar
# but put them in right after invoking tar.
#----------------------------------------------------------------------
NOW=`date "+%Y%m%d_%H%M%S"`
CGI_BIN=web/glossifier/cgi-bin
GLOSSIFIER_HOME=home/glossifier
BIN=$GLOSSIFIER_HOME/bin
GLOSSIFIER_BACKUP=/$GLOSSIFIER_HOME/backup
BACKUP=$GLOSSIFIER_BACKUP/glossifier_backup_$NOW.tar.bz2
PYMODULES=usr/local/cdr/lib/Python
SUDO=/usr/bin/sudo
LOGDIR=/usr/local/cdr/log

#----------------------------------------------------------------------
# Back up the old files.
#----------------------------------------------------------------------
if [ ! -d $GLOSSIFIER_BACKUP ]
then
    echo -n "creating $GLOSSIFIER_BACKUP..."
    $SUDO -u glossifier /bin/mkdir $GLOSSIFIER_BACKUP
    echo "done"
fi
echo -n "backing up old files to $BACKUP..."
$SUDO -u glossifier /bin/tar -cjf $BACKUP -C / $CGI_BIN $BIN $PYMODULES
echo "done"

#----------------------------------------------------------------------
# Fix the paths which need leading slashes, now that we don't have to
# worry about tar's warning message about stripping them.
#----------------------------------------------------------------------
CGI_BIN=/$CGI_BIN
BIN=/$BIN
PYMODULES=/$PYMODULES

#----------------------------------------------------------------------
# Clear out old versions.
#----------------------------------------------------------------------
echo -n "clearing out old versions of files..."
$SUDO -u glossifier /bin/rm -rf $CGI_BIN/* $BIN/*
$SUDO -u cdroperator /bin/rm -rf $PYMODULES/*
echo "done"

#----------------------------------------------------------------------
# Replace with the new sets.
#----------------------------------------------------------------------
echo -n "installing new files..."
$SUDO -u glossifier  /bin/cp -f $SRC_DIR/cgi-bin/* $CGI_BIN
$SUDO -u glossifier  /bin/cp -f $SRC_DIR/util/* $BIN
$SUDO -u cdroperator /bin/cp -f $SRC_DIR/Python/* $PYMODULES
echo "done"

#----------------------------------------------------------------------
# List the files in the locations of interest.
#----------------------------------------------------------------------
echo -e "\nCHECK PERMISSIONS IN THE FOLLOWING DIRECTORIES"
echo $CGI_BIN;   $SUDO -u glossifier  ls -l $CGI_BIN;   echo
echo $BIN;       $SUDO -u glossifier  ls -l $BIN;       echo
echo $PYMODULES; $SUDO -u cdroperator ls -l $PYMODULES; echo
echo $LOGDIR;    $SUDO -u cdroperator ls -l $LOGDIR;    echo
echo "======= Finished deployment of Glossifier files ======"
