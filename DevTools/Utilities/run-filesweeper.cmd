@echo off
REM Run the filesweeper scheduled job from the command line.
setlocal
d:
cd \cdr\Scheduler
set NDSCHEDULER_SETTINGS_MODULE=Scheduler.settings
set PYTHONPATH=d:/cdr/lib/Python;d:/cdr
set HOOVER_CONFIG=d:/cdr/Scheduler/tasks/FileSweeper.cfg
python -m tasks.file_sweeper_task %HOOVER_CONFIG% %*
