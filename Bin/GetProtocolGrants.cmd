@echo off
setlocal
set JDK=d:/usr/local/jdk
set CDR=d:/cdr
set CLASSPATH=%CDR%/lib;%JDK%/lib/classes12.zip;%JDK%/jre/lib/rt.jar
set PATH=%JDK%\bin;%PATH%
java GetProtocolGrants > ProtocolGrants.txt
endlocal
