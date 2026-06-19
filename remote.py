import logging
import os
import re
import shutil
import subprocess

_REMOTE_PATTERN = re.compile(r'^[^@]+@[^:]+:.+')


def is_remote(path):
    """Return True if path is a remote rsync destination (user@host:/path)."""
    return bool(_REMOTE_PATTERN.match(path))


def rsync(src, dest):
    """Copy src to dest using rsync over SSH.

    Appends trailing slashes for directory sources so rsync copies contents
    into the named destination (matching shutil.move behaviour).
    Deletes local src on success. Returns True on success, False on failure."""
    is_dir = os.path.isdir(src)
    cmd_src = src.rstrip('/') + '/' if is_dir else src
    cmd_dest = dest.rstrip('/') + '/' if is_dir else dest

    result = subprocess.run(['rsync', '-a', '--mkpath', cmd_src, cmd_dest])
    if result.returncode != 0:
        logging.error('rsync failed [exit %d]: [%s] -> [%s]', result.returncode, src, dest)
        return False

    if is_dir:
        shutil.rmtree(src)
    else:
        os.remove(src)
    logging.info('rsync succeeded, removed local copy: [%s]', src)
    return True
