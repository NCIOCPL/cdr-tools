#----------------------------------------------------------------------
#
# $Id$
#
# Rebuilds the manifest used to keep CDR client files up-to-date.
# Rewrite of original utility by Jeff Holmes 2002-05-14.
#
#----------------------------------------------------------------------
import cdr
import hashlib
import lxml.etree as etree
import sys
import socket
import os

CLIENT_FILES_DIR = len(sys.argv) > 1 and sys.argv[1] or cdr.CLIENT_FILES_DIR
MANIFEST_PATH    = "%s/%s" % (CLIENT_FILES_DIR, cdr.MANIFEST_NAME)

class File:
    """
    Objects representing each file in the client area. We will eventually
    eliminate the timestamp, after we have successfully transitioned all
    of the tiers to use checksums instead for detecting changes in files.
    We don't calculate the checksum in the File object's constructor,
    because we need to calculate a cumulative checksum representing all
    of the files, and we have to wait until all of the files have been
    collected and sorted before we do that (to ensure that the bytes for
    the files are fed into the hash in the same order every time we do
    this). So to avoid reading each file twice, we wait and calculate
    the checksums for the individual files after the File objects have
    been constructed and sorted.

    2016-04-05: Eliminating timestamps as promised.
    """
    def __init__(self, path):
        self.name = unicode(path, "latin-1")
        self.key = self.name.lower() # for sorting
    def __cmp__(self, other):
        "Sort by file names, ignoring case."
        return cmp(self.key, other.key)

def gather_files(dir_path):
    """
    Recursively gather a list all the files in the client files area.
    """
    files = []
    for name in os.listdir(dir_path):
        this_path = os.path.join(dir_path, name)
        if os.path.isdir(this_path):
            files += gather_files(this_path)
        else:
            files.append(File(this_path))
    return files

def create_ticket(md5):
    """
    Create a block for the manifest which can be used for a quick
    determination that at least one file is different (or missing)
    between the client and the server.
    """
    ticket = etree.Element("Ticket")
    etree.SubElement(ticket, "Application").text = sys.argv[0]
    etree.SubElement(ticket, "Host").text = str(socket.gethostname())
    etree.SubElement(ticket, "Author").text = str(os.environ["USERNAME"])
    etree.SubElement(ticket, "Checksum").text = md5.hexdigest().lower()
    return ticket

def md5(bytes):
    """
    Generate a checksum for the bytes from a file; used to detect when
    a file has changed.
    """
    m = hashlib.md5()
    m.update(bytes)
    return m.hexdigest().lower()

def create_filelist(files, manifest_md5):
    """
    Create a block for the manifest with a list of information for each
    of the files in the client area.
    """
    wrapper = etree.Element("FileList")
    for f in files:
        child = etree.SubElement(wrapper, "File")
        etree.SubElement(child, "Name").text = f.name
        if cdr.MANIFEST_NAME not in f.name:
            fp = open(f.name, "rb")
            bytes = fp.read()
            fp.close()
            etree.SubElement(child, "Checksum").text = md5(bytes)
            manifest_md5.update(bytes)
    return wrapper

def write_manifest(manifest_xml):
    """
    Serialize the manifest file to disk.
    Right now we also change the date/time stamp for the file on disk
    to the value we stored in the manifest for itself, but we'll
    eliminate once support for using checksums instead of file stamps
    has been deployed to all of the tiers.

    2016-04-05: date/time stamp dropped as promised.
    """
    manifest_file = file(MANIFEST_PATH, 'w')
    manifest_file.write(manifest_xml)
    manifest_file.close()

def refresh_manifest(where):
    """
    Top-level logic for this tool:

       1. Remove the previous copy of the manifest.
       2. Switch the current directory to the client files area.
       3. Collect File objects for the files in this area.
       4. Add a File object for the manifest file we're creating.
       5. Calculate the checksums for the files.
       6. Serialize the manifest to disk.
       7. Adjust the permissions for the client area files/directories.
    """
    try:
        os.unlink(MANIFEST_PATH)
    except:
        pass
    os.chdir(where)
    files = gather_files('.')
    files.append(File(os.path.join('.', cdr.MANIFEST_NAME)))
    files.sort()
    md5 = hashlib.md5()
    filelist = create_filelist(files, md5)
    root = etree.Element("Manifest")
    root.append(create_ticket(md5))
    root.append(filelist)
    xml = etree.tostring(root, pretty_print=True)
    write_manifest(xml)

    # NOTE: May change this in future to invoke something like
    #       BuildDeploy.findCygwin(), but for now, can't count on
    #       that being in the path, or findCygwin() being in cdr.py
    result = cdr.runCommand("D:\\cygwin\\bin\\chmod -R 777 *")
    if result.code:
        print "chmod return code: %s" % result.code
        if result.output:
            print result.output

if __name__ == "__main__":
    """
    Make it possible to load this file as a module without unwanted
    side effects.
    """
    refresh_manifest(CLIENT_FILES_DIR)
