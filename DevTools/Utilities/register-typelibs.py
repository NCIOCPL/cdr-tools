#----------------------------------------------------------------------
# Register typelibs needed by CDR. Do this after upgrade of Python.
# JIRA::OCECDR-4114
#----------------------------------------------------------------------
import os
import re
import subprocess
from win32com.client import selecttlb

class ActiveStatePython:
    SITE_PACKAGES = r"\Python\Lib\site-packages"
    WIN32COM = r"%s\win32com" % SITE_PACKAGES
    def __init__(self):
        self.win32com = None
        for drive in "DCEFG":
            path = r"%s:%s" % (drive, self.WIN32COM)
            if os.path.isdir(path):
                self.win32com = path
                self.drive = drive
                break
        if self.win32com is None:
            raise Exception("can't find %s" % self.SITE_PACKAGES)

class TLB:
    python = ActiveStatePython()
    gen_py = r"%s\gen_py" % python.win32com
    makepy = r"%s\client\makepy.py" % python.win32com
    #"python D:\Python\Lib\site-packages\win32com\client\makepy.py"
    patterns = (
        r"Microsoft ActiveX Data Objects \d+.\d+ Library",
        r"Microsoft ActiveX Data Objects Recordset \d+.\d+ Library",
        r"Microsoft ADO Ext. \d+.\d+ for DDL and Security"
    )
    tlbs = {}
    def __init__(self, tlb):
        self.desc = tlb.desc
        self.dll = tlb.dll
        self.version = (tlb.major, tlb.minor)
        for pattern in self.patterns:
            match = re.match(pattern, self.desc, re.I)
            if match:
                t = self.tlbs.get(pattern)
                if not t or t.version < self.version:
                    self.tlbs[pattern] = self
                    break
    def show(self):
        print self.dll, self.desc

    def register(self):
        cmd = "python %s \"%s\"" % (self.makepy, self.dll)
        stream = subprocess.Popen(cmd, shell=True,
                                  stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT)
        output, error = stream.communicate()
        code = stream.returncode
        if code:
            raise Exception("can't register %s (%s)" % (self.dll, self.desc))
        print "registered",
        self.show()

    @classmethod
    def reg_tlbs(cls):
        for key in cls.tlbs:
            cls.tlbs[key].register()

    @classmethod
    def show_tlbs(cls):
        for key in cls.tlbs:
            cls.tlbs[key].show()

    @staticmethod
    def find_tlbs():
        for tlb in selecttlb.EnumTlbs():
            TLB(tlb)

if __name__ == "__main__":
    if not os.path.isdir(TLB.gen_py):
        os.mkdir(TLB.gen_py)
        if not os.path.isdir(TLB.gen_py):
            raise Exception("can't create %s" % TLB.gen_py)
        print "created", TLB.gen_py
    TLB.find_tlbs()
    #TLB.show_tlbs()
    TLB.reg_tlbs()
