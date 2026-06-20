import logging
import os
import re
import shutil
import subprocess

_REMOTE_PATTERN = re.compile(r'^[^@]+@[^:]+:.+')


def is_remote(path):
    """Return True if path is a remote rsync destination (user@host:/path)."""
    return bool(_REMOTE_PATTERN.match(path))


_REMOTE_HOST_PATH = re.compile(r'^([^@]+@[^:]+):(.+)')


def _mkdir_remote(dest, is_dir):
    """Create the remote directory via SSH before rsync (--mkpath requires rsync 3.2.3+)."""
    m = _REMOTE_HOST_PATH.match(dest)
    if not m:
        return
    host, path = m.group(1), m.group(2)
    remote_dir = path if is_dir else os.path.dirname(path)
    subprocess.run(['ssh', host, f'mkdir -p "{remote_dir}"'], capture_output=True)


def rsync(src, dest):
    """Copy src to dest using rsync over SSH.

    Appends trailing slashes for directory sources so rsync copies contents
    into the named destination (matching shutil.move behaviour).
    Deletes local src on success. Returns True on success, False on failure."""
    is_dir = os.path.isdir(src)
    cmd_src = src.rstrip('/') + '/' if is_dir else src
    cmd_dest = dest.rstrip('/') + '/' if is_dir else dest

    if is_remote(dest):
        _mkdir_remote(dest, is_dir)

    result = subprocess.run(['rsync', '-a', cmd_src, cmd_dest], capture_output=True)
    if result.returncode != 0:
        logging.error('rsync failed [exit %d]: [%s] -> [%s]\n%s',
                      result.returncode, src, dest, result.stderr.decode(errors='replace'))
        return False

    if is_dir:
        shutil.rmtree(src)
    else:
        os.remove(src)
    logging.info('rsync succeeded, removed local copy: [%s]', src)
    return True
