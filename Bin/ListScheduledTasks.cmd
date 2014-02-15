@ECHO OFF
SETLOCAL
C:
CD \Windows\Tasks
C:\Windows\system32\schtasks.EXE /Query /XML ONE > D:\cdr\Reports\schtasks.tmp
MOVE /Y D:\cdr\Reports\schtasks.tmp D:\cdr\Reports\schtasks.xml
D:
CD \cdr\Reports
D:\cygwin\bin\chmod.exe 644 schtasks.xml
