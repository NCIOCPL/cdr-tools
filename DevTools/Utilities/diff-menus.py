#!/usr/bin/env python
"""Find CDR Admin scripts which need to be tested.

The Developers menu has the largest set of scripts, so it makes
sense to test the scripts on on that menu first. Having done that,
only a relatively small number of scripts will be found on the other
menus which aren't also on the "Developers" menu. This script finds
and reports on the scripts which still need to be tested after you
have tested all the scripts on one or more of the other menus.

Example usage:

  ./diff-menus.py --tested Developers
  ./diff-menus.py --tested Developers "Board Managers"
"""

from argparse import ArgumentParser
from functools import cached_property
from cdrcgi import HTMLPage


class MenuChecker:
    """Compare a menu we've already tested with another menu."""

    INDENT = 4

    @cached_property
    def menus(self):
        menus = {}
        for menu in HTMLPage.load_menus():
            menus[menu["label"]] = menu
        return menus

    @cached_property
    def opts(self):
        choices = sorted(self.menus)
        opts = dict(nargs="+", action="extend", choices=choices, required=True)
        parser = ArgumentParser()
        parser.add_argument("--tested", "-t", **opts)
        return parser.parse_args()

    @cached_property
    def report(self):
        def collect(menu, depth=0):
            lines = []
            for child in menu["children"]:
                if "children" in child:
                    lines += collect(child, depth+1)
                else:
                    script = child["script"]
                    key = script.lower()
                    if key not in self.tested and key not in self.untested:
                        label = child["label"]
                        indent = " " * self.INDENT * (depth + 1)
                        lines.append(f"{indent}{label} ({script})")
                        self.untested.add(key)
            if not lines:
                return []
            if depth < 0:
                return lines
            indent = " " * self.INDENT * depth
            label = menu["label"]
            return [f"{indent}{label}"] + lines
        report_lines = []
        for name in self.menus:
            if name not in self.opts.tested:
                report_lines += collect(self.menus[name])
        return "\n".join(report_lines)

    @cached_property
    def tested(self):
        tested = set()
        def collect(menu):
            script = menu.get("script")
            if script:
                tested.add(script.lower())
            else:
                for child in menu["children"]:
                    collect(child)
        for name in self.opts.tested:
            collect(self.menus[name])
        return tested

    @cached_property
    def untested(self):
        return set()


if __name__ == "__main__":
    """Run the report when this file is execute (not imported as a module)."""

    checker = MenuChecker()
    print(checker.report)
    print(f"\n{len(checker.untested)} scripts still need to be tested.")
