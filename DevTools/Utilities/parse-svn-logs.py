#----------------------------------------------------------------------
# Script to find files/directories changed since a certain point in
# history.
#
# Example usage:
#  svn log -v %CDRREPO%/branches/Curie | parse-svn-logs.py -d 2015-08-01 \
#   -e /branches/Curie/ebms -e /branches/Curie/Dev
#----------------------------------------------------------------------
import argparse
import re

class Path:
    " Information about a file or directory's last commit action"
    def __init__(self, revision, date, user, action):
        self.revision = revision
        self.date = date
        self.user = user
        self.action = action

#----------------------------------------------------------------------
# Collect the command-line arguments.
#----------------------------------------------------------------------
desc = "Find files and directories changed since a start date or revision."
parser = argparse.ArgumentParser(description=desc)
parser.add_argument("--logfile", "-l", help="Subversion log output to parse",
                    type=argparse.FileType("r"), default="-")
group = parser.add_mutually_exclusive_group()
group.add_argument("--exclude", "-e", help="path to exclude", action="append")
group.add_argument("--include", "-i", help="path to include", action="append")
group = parser.add_mutually_exclusive_group()
group.add_argument("--start-date", "-d",
                   help="include commits on or after this date")
group.add_argument("--start-revision", "-r", type=int,
                   help="include revisions after this")
opts = parser.parse_args()

#----------------------------------------------------------------------
# Parse from top of the log file until we hit the stopping point.
#----------------------------------------------------------------------
new_revision = path_list = False
paths = {}
for line in opts.logfile:
    line = line.strip()
    if new_revision:
        pieces = line.split()
        revision = int(pieces[0][1:])
        user = pieces[2]
        date = pieces[4]
        if opts.start_date and date < opts.start_date:
            break
        if opts.start_revision and revision < opts.start_revision:
            break
        new_revision = False
    elif path_list:
        if not line:
            path_list = False
        else:
            action, path = line.split(" ", 1)
            path = path.split(" (from /")[0]
            if path not in paths:
                if opts.exclude:
                    if any([path.startswith(e) for e in opts.exclude]):
                        continue
                if opts.include:
                    if not any([path.startswith(i) for i in opts.include]):
                        continue
                paths[path] = Path(revision, date, user, action)
    if line == "-" * 72:
        new_revision = True
    elif line == "Changed paths:":
        path_list = True

#----------------------------------------------------------------------
# Show the files/directories in order by name. Include action code
# (A=added, M=modified, D=Deleted) at the front of each line.
#----------------------------------------------------------------------
for path in sorted(paths):
    print paths[path].action, path
