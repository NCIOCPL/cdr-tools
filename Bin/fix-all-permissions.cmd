@echo off
setlocal
rem ======================================================================
rem Run this script using your aa account prior to deploying a release.
rem This will take a few minutes to complete.
rem
rem https://collaborate.nci.nih.gov/display/OCECTBWIKI/CDR+Release+Deployment+How-To
rem ======================================================================
set FIX_PERMS=d:\cdr\Bin\fix-permissions.cmd
call %FIX_PERMS% d:\cdr\Bin
call %FIX_PERMS% d:\cdr\ClientFiles
call %FIX_PERMS% d:\cdr\Database
call %FIX_PERMS% d:\cdr\lib
call %FIX_PERMS% d:\cdr\Licensee
call %FIX_PERMS% d:\cdr\Mailers
call %FIX_PERMS% d:\cdr\Publishing
call %FIX_PERMS% d:\cdr\Scheduler
call %FIX_PERMS% d:\cdr\Schemas
call %FIX_PERMS% d:\cdr\Utilities
call %FIX_PERMS% d:\Inetpub\wwwroot
endlocal
