# Remote Copy (Synology NAS) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add rsync-based remote copy support so that `seriesDir` and `movieDir` can be specified as `user@host:/path` destinations, with ntfy push notification on failure.

**Architecture:** Two new modules (`ntfy.py`, `remote.py`) follow the existing one-module-per-integration pattern. `move_movies` and `move_series` in `CopyMedia` are converted from `@staticmethod` to instance methods to access ntfy config, then extended to dispatch to rsync when the destination is remote.

**Tech Stack:** Python 3, `requests` (already installed in `.venv/`), `rsync` CLI (must be available on `PATH`, 3.2.3+ for `--mkpath`), `unittest.mock` for subprocess mocking.

## Global Constraints

- Activate venv before running anything: `source .venv/bin/activate`
- Run tests with: `python3 -m unittest <test_file>`
- All new config fields are optional — absence must be handled silently
- rsync 3.2.3+ required for `--mkpath` flag
- Local file/dir is deleted only on rsync success; kept on failure
- ntfy notification is sent on rsync failure only if both `ntfyUrl` and `ntfyToken` are configured
- Do not delete local file on ntfy send failure

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `ntfy.py` | Create | HTTP POST to ntfy channel with Bearer auth |
| `remote.py` | Create | Remote path detection and rsync subprocess wrapper |
| `test_remote.py` | Create | Unit tests for `ntfy.py` and `remote.py` |
| `copy_files.py` | Modify | Import new modules; add ntfy instance vars; update `process_configs`; convert `move_movies` and `move_series` to instance methods with remote dispatch |
| `test_copy_files.py` | Modify | Add test verifying ntfy config is loaded from `process_configs` |
| `test_resources/test_CopyMedia.json` | Modify | Add `ntfyUrl` and `ntfyToken` fields for config loading test |

---

### Task 1: ntfy.py

**Files:**
- Create: `ntfy.py`
- Create: `test_remote.py` (initial skeleton + ntfy tests)

**Interfaces:**
- Produces: `ntfy.send_notification(url: str, token: str, message: str) -> requests.Response | None`

- [ ] **Step 1: Write the failing test**

Create `test_remote.py`:

```python
#!/usr/bin/python3
import os
import unittest
from unittest.mock import MagicMock, patch

import logger
import ntfy

logger.config()

NTFY_CONTEXT_VAR = 'NTFY_CONTEXT'


class TestNtfy(unittest.TestCase):

    def test_send_notification(self):
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            result = ntfy.send_notification('https://ntfy.sh/topic', 'mytoken', 'test message')

            mock_post.assert_called_once_with(
                'https://ntfy.sh/topic',
                data='test message',
                headers={'Authorization': 'Bearer mytoken'}
            )
            self.assertEqual(result.status_code, 200)

    def test_send_notification_live(self):
        """Live test — set NTFY_CONTEXT=https://ntfy.sh/<topic>|<token> to run."""
        ntfy_context = os.getenv(NTFY_CONTEXT_VAR)
        if ntfy_context is None:
            self.skipTest('Set NTFY_CONTEXT=https://ntfy.sh/<topic>|<token> to run this test')
        url, token = ntfy_context.split('|', 1)
        r = ntfy.send_notification(url, token, 'CopyMedia test notification')
        self.assertEqual(r.status_code, 200)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
source .venv/bin/activate
python3 -m unittest test_remote.TestNtfy.test_send_notification -v
```

Expected: `ModuleNotFoundError: No module named 'ntfy'`

- [ ] **Step 3: Create ntfy.py**

```python
import logging
import requests


def send_notification(url, token, message):
    """POST a plain-text message to an ntfy channel with Bearer auth.

    Returns the Response on success, None if an exception occurs (logged, not raised)."""
    try:
        r = requests.post(url, data=message, headers={'Authorization': 'Bearer ' + token})
        r.raise_for_status()
        return r
    except Exception:
        logging.exception('Failed to send ntfy notification to [%s]', url)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python3 -m unittest test_remote.TestNtfy.test_send_notification -v
```

Expected: `PASS`

- [ ] **Step 5: Commit**

```bash
git add ntfy.py test_remote.py
git commit -m "feat: add ntfy notification module and test"
```

---

### Task 2: remote.py

**Files:**
- Create: `remote.py`
- Modify: `test_remote.py` (add `TestRemote` class)

**Interfaces:**
- Consumes: nothing from prior tasks
- Produces:
  - `remote.is_remote(path: str) -> bool`
  - `remote.rsync(src: str, dest: str) -> bool` — runs rsync, deletes local `src` on success, returns `True`/`False`

- [ ] **Step 1: Write failing tests for is_remote**

Add this class to `test_remote.py` (after the existing `TestNtfy` class):

```python
import shutil
import tempfile
from remote import is_remote, rsync


class TestRemote(unittest.TestCase):

    def test_is_remote_true(self):
        self.assertTrue(is_remote('david@nas:/volume1/plex'))
        self.assertTrue(is_remote('user@192.168.1.1:/path/to/dir'))
        self.assertTrue(is_remote('user@host:relative/path'))

    def test_is_remote_false(self):
        self.assertFalse(is_remote('/absolute/local/path'))
        self.assertFalse(is_remote('relative/path'))
        self.assertFalse(is_remote('path/with@symbol/in/dir/filename.mkv'))

    def test_rsync_success_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, 'episode.mkv')
            open(src, 'w').close()

            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                result = rsync(src, 'user@nas:/series/ShowName/episode.mkv')

            self.assertTrue(result)
            self.assertFalse(os.path.exists(src))

    def test_rsync_failure_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, 'episode.mkv')
            open(src, 'w').close()

            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=11)
                result = rsync(src, 'user@nas:/series/ShowName/episode.mkv')

            self.assertFalse(result)
            self.assertTrue(os.path.exists(src))

    def test_rsync_success_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, 'Toy_Story_4.2019')
            os.makedirs(src)
            open(os.path.join(src, 'movie.mkv'), 'w').close()

            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                result = rsync(src, 'user@nas:/movies/Toy_Story_4.2019')
                cmd = mock_run.call_args[0][0]

            self.assertTrue(result)
            self.assertFalse(os.path.exists(src))
            # Trailing slash must be added to both src and dest for directory rsync
            self.assertTrue(cmd[3].endswith('/'))
            self.assertTrue(cmd[4].endswith('/'))

    def test_rsync_failure_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, 'Toy_Story_4.2019')
            os.makedirs(src)

            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=11)
                result = rsync(src, 'user@nas:/movies/Toy_Story_4.2019')

            self.assertFalse(result)
            self.assertTrue(os.path.exists(src))
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 -m unittest test_remote.TestRemote -v
```

Expected: `ModuleNotFoundError: No module named 'remote'`

- [ ] **Step 3: Create remote.py**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m unittest test_remote.TestRemote -v
```

Expected: all 6 tests `PASS`

- [ ] **Step 5: Run full test_remote suite**

```bash
python3 -m unittest test_remote -v
```

Expected: all tests pass (live test skipped without env var)

- [ ] **Step 6: Commit**

```bash
git add remote.py test_remote.py
git commit -m "feat: add remote detection and rsync module with tests"
```

---

### Task 3: Wire up in copy_files.py

**Files:**
- Modify: `copy_files.py`
- Modify: `test_copy_files.py` (add ntfy config loading test)
- Modify: `test_resources/test_CopyMedia.json` (add ntfy fields)

**Interfaces:**
- Consumes:
  - `remote.is_remote(path: str) -> bool`
  - `remote.rsync(src: str, dest: str) -> bool`
  - `ntfy.send_notification(url: str, token: str, message: str) -> Response | None`

- [ ] **Step 1: Add ntfy fields to test config**

Edit `test_resources/test_CopyMedia.json` to add at the top level alongside `series`:

```json
{
    "ntfyUrl": "https://ntfy.sh/test-topic",
    "ntfyToken": "test-token-abc",
    "series": [
        {
            "name": "World Trigger",
            "regex": "(.*)(World Trigger)( - )(\\d{1,})(.*)"
        },
        {
            "name": "That Time I Got Reincarnated as a Slime",
            "regex": "(.*)(Tensei Shitara Slime Datta Ken)( - )(\\d{1,})(.*)",
            "replace": "\\1That Time I Got Reincarnated as a Slime\\3\\4\\5"
        },
        {
            "name": "One-Punch Man",
            "destination":"One Punch Man",
            "regex": "(.*)(One-Punch Man)( - )(\\d{1,})(.*)"
        }
    ]
}
```

- [ ] **Step 2: Write failing test for ntfy config loading**

Add this test to the `TestCopyMedia` class in `test_copy_files.py` (after `test_process_configs`):

```python
def test_process_configs_ntfy(self):
    series_path = '/remote/test/series'
    movie_path = '/remote/test/movies'
    test_file = '/home/test/dir/file'

    # ntfy config loaded from file when not supplied via constructor
    c = CopyMedia(config_file=TEST_CONFIG, seriesdir=series_path, file=test_file,
                  moviedir=movie_path)
    self.assertEqual('https://ntfy.sh/test-topic', c.ntfy_url)
    self.assertEqual('test-token-abc', c.ntfy_token)

    # constructor args override config file values
    c2 = CopyMedia(config_file=TEST_CONFIG, seriesdir=series_path, file=test_file,
                   moviedir=movie_path, ntfy_url='https://ntfy.sh/override',
                   ntfy_token='override-token')
    self.assertEqual('https://ntfy.sh/override', c2.ntfy_url)
    self.assertEqual('override-token', c2.ntfy_token)
```

- [ ] **Step 3: Run test to verify it fails**

```bash
python3 -m unittest test_copy_files.TestCopyMedia.test_process_configs_ntfy -v
```

Expected: `AttributeError: 'CopyMedia' object has no attribute 'ntfy_url'`

- [ ] **Step 4: Add imports and class attributes to copy_files.py**

At the top of `copy_files.py`, add two imports alongside the existing module imports (after `from exceptions import ConfigurationError`):

```python
import ntfy
import remote
```

In the `CopyMedia` class body, add two class attributes alongside the existing ones (after `tmdb_key = None`):

```python
ntfy_url = None
ntfy_token = None
```

- [ ] **Step 5: Update __init__ signature and body**

Replace the `__init__` signature and instance variable assignments:

```python
def __init__(self, logfile=None, config_file=None, ifttt_url=None, scandir=None,
             seriesdir=None, file=None, tmdb_key=None, moviedir=None,
             ntfy_url=None, ntfy_token=None):
    self.file = file
    self.logfile = logfile
    self.config_file = config_file
    self.ifttt_url = ifttt_url
    self.scandir = scandir
    self.seriesdir = seriesdir
    self.moviedir = moviedir
    self.tmdb_key = tmdb_key
    self.ntfy_url = ntfy_url
    self.ntfy_token = ntfy_token
```

- [ ] **Step 6: Update process_configs to read ntfy config**

In `process_configs`, after the IFTTT logging block (lines 444–448), add:

```python
if self.ntfy_url is None and 'ntfyUrl' in config:
    self.ntfy_url = config['ntfyUrl']
if self.ntfy_token is None and 'ntfyToken' in config:
    self.ntfy_token = config['ntfyToken']

if self.ntfy_url and self.ntfy_token:
    logging.debug('ntfy URL: [%s]', self.ntfy_url)
else:
    logging.debug('ntfy notification not configured.')
```

- [ ] **Step 7: Run test to verify config loading passes**

```bash
python3 -m unittest test_copy_files.TestCopyMedia.test_process_configs_ntfy -v
```

Expected: `PASS`

- [ ] **Step 8: Convert move_movies to instance method with remote dispatch**

Replace the entire `move_movies` static method (lines 487–499) with:

```python
def move_movies(self, movie_files, move_dir):
    """Move movie files to the specified destination directory"""

    logging.debug('Moving movie files: [%s]', movie_files)
    for movie in movie_files:
        start_path = movie
        dest_path = join(move_dir, path.basename(movie))
        logging.debug('Moving [%s] to [%s]...', start_path, dest_path)
        if remote.is_remote(move_dir):
            if not remote.rsync(start_path, dest_path):
                if self.ntfy_url and self.ntfy_token:
                    ntfy.send_notification(
                        self.ntfy_url, self.ntfy_token,
                        'CopyMedia: rsync failed moving [%s] to [%s]' % (start_path, dest_path)
                    )
        else:
            shutil.move(start_path, dest_path)
            logging.info('Successfully moved [%s] to [%s]', start_path, dest_path)
```

- [ ] **Step 9: Convert move_series to instance method with remote dispatch**

Replace the entire `move_series` static method (lines 501–533) with:

```python
def move_series(self, matches, move_dir, start_dir):
    """Move matching series files to their respective destination directory"""

    destinations = set()

    for file_name, config_entry in matches:

        dest_file_name = CopyMedia.build_new_name(file_name, config_entry)

        if 'destination' in config_entry:
            dest = join(move_dir, config_entry['destination'])
        else:
            dest = join(move_dir, config_entry['name'])

        logging.debug('Destination directory: [%s]', dest)

        src_path = join(start_dir, file_name)
        dest_path = join(dest, dest_file_name)

        if remote.is_remote(move_dir):
            logging.debug('Moving [%s] to [%s]...', src_path, dest_path)
            if not remote.rsync(src_path, dest_path):
                if self.ntfy_url and self.ntfy_token:
                    ntfy.send_notification(
                        self.ntfy_url, self.ntfy_token,
                        'CopyMedia: rsync failed moving [%s] to [%s]' % (src_path, dest_path)
                    )
        else:
            if not path.exists(dest):
                logging.info('Destination does not exist; creating [%s]', dest)
                makedirs(dest)
            logging.debug('Moving [%s] to [%s]...', src_path, dest_path)
            shutil.move(src_path, dest_path)
            logging.info('Successfully moved [%s] to [%s]', src_path, dest_path)

        destinations.add(dest)

    return destinations
```

- [ ] **Step 10: Run the full test suite**

```bash
python3 -m unittest test_copy_files -v
python3 -m unittest test_remote -v
```

Expected: all tests pass (live tests skipped without env vars)

- [ ] **Step 11: Commit**

```bash
git add copy_files.py test_copy_files.py test_resources/test_CopyMedia.json
git commit -m "feat: wire remote rsync and ntfy notification into CopyMedia"
```
