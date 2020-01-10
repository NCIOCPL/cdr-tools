#!/usr/bin/env python

"""
Tool to find function or method invocations in source code

NOTE: Be aware that there are limitations to this tool. The Python
ast module, on which this program depends for information about the
function calls in the source code, does not report the qualified
name of the function being called (so it's impossible to distinguish
between a call to cdrcgi.bail() and foobar.bail()), and it won't
recognize calls to a function which have been given an alias (for
example, if a module has `from cdrcgi import bail as webbail`,
then the tool will find calls to "webbail" but not to "bail").
You'll have to use other tools to find out about such imports
(though imports aren't the only way to alias a function or
method).
"""

import argparse
import ast
import os

class Finder:
    """Control object for tool"""

    def __init__(self):
        """Collect command-line options"""
        parser = argparse.ArgumentParser()
        parser.add_argument("name")
        parser.add_argument("--top", default=".")
        parser.add_argument("--show-arg-counts", action="store_true")
        parser.add_argument("--show-keywords", action="store_true")
        parser.add_argument("--show-locations", action="store_true")
        parser.add_argument("--list-files", action="store_true")
        parser.add_argument("--dump", action="store_true")
        parser.add_argument("--minargs", type=int, default=0)
        parser.add_argument("--minkeywords", type=int, default=0)
        parser.add_argument("--skip", nargs="*", default=["ebms"])
        parser.add_argument("--extension", default=".py")
        self.opts = parser.parse_args()

    def run(self):
        """Walk through the source code set and report matches"""
        message = f"{{}} has call to {self.opts.name}()"
        for basepath, dirs, files in os.walk(self.opts.top, topdown=True):
            if self.opts.skip:
                dirs[:] = [d for d in dirs if d not in self.opts.skip]
            for filename in files:
                if self.opts.skip is not None and filename in self.opts.skip:
                    continue
                if filename.lower().endswith(self.opts.extension):
                    path = f"{basepath}/{filename}"
                    tree = self.__parse(path)
                    for node in ast.walk(tree):
                        if self.__wanted(node):
                            pieces = [message.format(path)]
                            if self.opts.list_files:
                                print(path.replace("\\", "/"))
                                break
                            if self.opts.show_locations:
                                pieces.append(f"at line {node.lineno:d},")
                                pieces.append(f"column {node.col_offset:d}")
                            if self.opts.show_arg_counts:
                                pieces.append(f"with {len(node.args):d} args")
                                pieces.append(f"and {len(node.keywords):d}")
                                pieces.append("keyword args")
                            if self.opts.show_keywords and node.keywords:
                                names = [k.arg for k in node.keywords]
                                pieces.append(f"(kw={', '.join(names)})")
                            print(" ".join(pieces))
                            if self.opts.dump:
                                print(ast.dump(node, True, True))

    def __parse(self, path):
        """
        Get the AST for the source code file

        Pass:
          path - location of the file to be loaded and parsed

        Return:
          parsed source code object
        """

        with open(path) as fp:
            try:
                source = fp.read()
            except:
                print(path)
                raise
        return ast.parse(source, path)

    def __wanted(self, node):
        """
        Find out if this node matches our search criteria

        Pass:
          node - object for a node in the source tree

        Return:
          True if the object matches our filtering criteria
        """

        if not isinstance(node, ast.Call):
            return False
        if len(node.args) < self.opts.minargs:
            return False
        if len(node.keywords) < self.opts.minkeywords:
            return False
        if isinstance(node.func, ast.Attribute):
            return self.opts.name == node.func.attr
        if isinstance(node.func, ast.Name):
            return self.opts.name == node.func.id
        return False


if __name__ == "__main__":
    Finder().run()
