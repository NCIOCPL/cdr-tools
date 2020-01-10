#!/usr/bin/env python

"""Compare filter sets across tiers.
"""

from argparse import ArgumentParser
from cdrapi.docs import FilterSet
from cdrapi.settings import Tier
from cdrapi.users import Session

def get_sets(tier):
    session = Session("guest", tier=tier)
    sets = {}
    for id, name in FilterSet.get_filter_sets(session):
        sets[name] = FilterSet(session, id=id)
    return sets

def get_members(members):
    lines = []
    for member in members:
        if isinstance(member, FilterSet):
            lines.append(f"filter set: {member.name}")
        else:
            lines.append(f"filter: {member.title}")
    return lines

parser = ArgumentParser()
parser.add_argument("--other_tier", default="PROD")
parser.add_argument("--local_tier", default=Tier().name)
opts = parser.parse_args()
local = get_sets(opts.local_tier)
other = get_sets(opts.other_tier)
other_names = sorted(other)
position = 0
banner = f"Comparing FilterSets between {opts.other_tier} and {opts.local_tier}"
for name in sorted(local):
    while position < len(other_names) and other_names[position] < name:
        if banner:
            print(banner)
            print()
            banner = None
        print(other_names[position])
        print(f"local name is {name!r}")
        print(f"other name is {other_names[position]!r}")
        print(f"  only on {opts.other_tier}")
        print()
        position += 1
    if position < len(other_names) and other_names[position] == name:
        position += 1
    if name in other:
        local_set = local[name]
        other_set = other[name]
        diffs = []
        for property in "name", "description", "notes", "members":
            local_property = getattr(local_set, property)
            other_property = getattr(other_set, property)
            if property == "members":
                local_property = get_members(local_property)
                other_property = get_members(other_property)
            if local_property != other_property:
                diff = property, local_property, other_property
                diffs.append(diff)
        if diffs:
            if banner:
                print(banner)
                print()
                banner = None
            print(name)
            for prop, local_prop, other_prop in diffs:
                print(f"  {opts.other_tier} {prop}: {other_prop!r}")
                print(f"  {opts.local_tier} {prop}: {local_prop!r}")
            print()
    else:
        if banner:
            print(banner)
            print()
            banner = None
        print(name)
        print(f"  only on {opts.local_tier}")
        print()
while position < len(other_names) and other_names[position] not in local:
    if banner:
        print(banner)
        print()
        banner = None
    print(other_names[position])
    print(f"  only on {opts.other_tier}")
    print()
    position += 1
