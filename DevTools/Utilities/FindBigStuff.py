import sys
# 100 megabytes (du uses kb)
threshold = 100000
# user can specify threshold in megabytes
if len(sys.argv) > 1:
    threshold = int(sys.argv[1]) * 1000
for line in sys.stdin.readlines():
    parts = line.split("\t")
    if len(parts) == 2:
        kbytes = int(parts[0])
        if kbytes > threshold:
            print line.strip()
