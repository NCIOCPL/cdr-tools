@echo off
if .%2. == .. goto usage

echo Comparing %1 %2
sabcmd \cdr\bin\indent.xml %1 > %TEMP%\diffx1.xml
sabcmd \cdr\bin\indent.xml %2 > %TEMP%\diffx2.xml

diff %TEMP%\diffx1.xml %TEMP%\diffx2.xml

rm %TEMP%\diffx1.xml %TEMP%\diffx2.xml

goto done

:usage
echo Usage: diffxml file1 file2
echo outputs to stdout

:done
