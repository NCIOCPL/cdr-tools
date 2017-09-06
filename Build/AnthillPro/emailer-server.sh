#!/bin/bash
#----------------------------------------------------------------------
# This script is a wrapper for deploying a new release for the CDR
# emailer server. It is copied to /cdr_deployments/$RELEASE where
# it is run by CBIIT. We use a separate script to make capturing
# and sending out the output from the deployment simpler and more
# reliable and to isolate into this smaller script the parts which
# need to be customized for each release.
#----------------------------------------------------------------------

#----------------------------------------------------------------------
# These are the only parts which needs to be tailored for each release.
#----------------------------------------------------------------------
RELEASE=REPLACEME
DEVELOPERS=EMAIL_ADDRESS_FOR_CDR_DEVELOPMENT_TEAM

#----------------------------------------------------------------------
# Set up the rest of the variables.
#----------------------------------------------------------------------
SUBJECT="Deployment of $RELEASE emailer server updates"
LOGNAME=`/bin/date +"$RELEASE-%Y%m%d%H%M%S.log"`
LINUX_DIR=/cdr_deployments/$RELEASE/linux
LOGPATH=$LINUX_DIR/$LOGNAME

#----------------------------------------------------------------------
# Invoke the script which does the actual deployment work.
#----------------------------------------------------------------------
echo -n "deploying $RELEASE to emailer server..."
$LINUX_DIR/Emailers/deploy.sh $LINUX_DIR/Emailers >> $LOGPATH 2>&1
echo done

#----------------------------------------------------------------------
# Send the output to the development team.
#----------------------------------------------------------------------
echo -n "sending output to $DEVELOPERS..."
/bin/mail -s "$SUBJECT" $DEVELOPERS < $LOGPATH
echo done
