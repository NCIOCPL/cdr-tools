#!/usr/bin/env python

"""
Create a CHECKSUMS file for exported CDR documents
"""

from argparse import ArgumentParser
from datetime import datetime
from functools import partial
from glob import glob
from hashlib import sha256
import os
from sys import stderr

class Control:

    def __init__(self):
        parser = ArgumentParser()
        parser.add_argument("--directory", required=True)
        self.opts = parser.parse_args()

    def checksum(self, path):
        hasher = sha256()
        with open(path, "rb") as fp:
            for block in iter(partial(fp.read, 4096), b""):
                hasher.update(block)
        return hasher.hexdigest()

    def run(self):
        start = datetime.now()
        os.chdir(self.opts.directory)
        types = [name for name in os.listdir(".") if os.path.isdir(name)]
        count = 0
        with open("CHECKSUMS", "w") as fp:
            for directory in sorted(types):
                paths = [path for path in glob("{}/CDR*".format(directory))]
                for path in sorted(paths, key=self.extract_id):
                    path = path.replace("\\", "/")
                    fp.write("{} {}\n".format(self.checksum(path), path))
                    count += 1
                    stderr.write("\rprocessed {:d} files".format(count))
        elapsed = (datetime.now() - start).total_seconds()
        stderr.write(" in {:f} seconds".format(elapsed))

    @staticmethod
    def extract_id(path):
        basename, extension = os.path.splitext(os.path.split(path)[-1])
        return int(basename[3:])

Control().run()
