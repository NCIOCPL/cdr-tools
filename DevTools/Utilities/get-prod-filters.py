from json import dump
from sys import stderr
from requests import get
from cdr import getFilters

URL = "https://cdr.cancer.gov/cgi-bin/cdr/ShowDocXml.py?DocId={}"

filters = {}
names_and_ids = getFilters("guest", tier="PROD")
for filt in names_and_ids:
    url = URL.format(filt.id)
    response = get(url)
    if response.status_code != 200:
        raise Exception(response.reason)
    filters[filt.name] = response.text
    stderr.write(f"\rfetched {len(filters)} of {len(names_and_ids)} filters")
with open("prod-filters.json", "w") as fp:
    dump(filters, fp)
stderr.write("\ndone\n")
