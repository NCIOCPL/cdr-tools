:again
d:\ntreskit\now >> d:\cdr\log\pstat.log
d:\ntreskit\pstat | d:\bin\grep sqlservr | d:\bin\grep pid: >> d:\cdr\log\pstat.log
d:\ntreskit\pstat | d:\bin\grep CdrServer | d:\bin\grep pid: >> d:\cdr\log\pstat.log
d:\ntreskit\sleep 60
goto again
