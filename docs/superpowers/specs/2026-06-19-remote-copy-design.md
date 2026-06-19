# Remote Copy (Synology NAS) Design

**Date:** 2026-06-19

## Overview

Add support for remote destinations in the form `user@host:/path` for both `seriesDir` and `movieDir`. When a destination is remote, use `rsync` over SSH instead of `shutil.move`. On success, delete the local file. On failure, leave the local file and send an ntfy push notification.

## Architecture

Two new modules, following the existing pattern of one module per external integration:

- **`remote.py`** — detects remote paths and wraps `rsync` subprocess calls
- **`ntfy.py`** — sends push notifications to an ntfy channel via HTTP POST

`move_movies` and `move_series` in `CopyMedia` are converted from `@staticmethod` to instance methods so they can access `self.ntfy_url` and `self.ntfy_token` without threading extra parameters through every call. These methods are internal and not directly unit tested, so the signature change is safe.

## Remote Path Detection and rsync (`remote.py`)

`is_remote(path)` matches `^[^@]+@[^:]+:.+` — loose enough to distinguish remote destinations from local paths without fully validating SSH syntax.

`rsync(src, dest)` runs:

```
rsync -a --mkpath <src> <dest>
```

- `-a` (archive mode) preserves permissions and timestamps
- `--mkpath` creates the remote directory tree automatically (requires rsync 3.2.3+)
- For **directory** sources (movie dirs), a trailing `/` is appended to `src` so rsync copies the contents into the named destination, matching `shutil.move` behaviour
- For **file** sources (series episodes), no trailing slash is needed
- Returns `True` on exit code 0, `False` otherwise; logs the exit code on failure

On success, the local file is deleted (`os.remove`) or the local directory is removed (`shutil.rmtree`).

In `move_series`, the `makedirs` call is skipped for remote destinations — `--mkpath` handles directory creation on the remote side.

## ntfy Integration (`ntfy.py`)

`send_notification(url, token, message)` POSTs `message` as plain text to `url` with header `Authorization: Bearer <token>`.

- On HTTP error or network failure, logs the exception but does not raise — a notification failure must not mask the original rsync failure
- Called from `move_movies` and `move_series` immediately after a failed rsync, before returning
- If `ntfy_url` or `ntfy_token` are not configured, the notification is silently skipped

Notification message format:
```
CopyMedia: rsync failed moving [<src>] to [<dest>]
```

## Configuration

Two new optional fields in `CopyMedia.json`:

```json
"ntfyUrl": "https://ntfy.sh/your-topic",
"ntfyToken": "your-auth-token"
```

`process_configs` reads these into `self.ntfy_url` and `self.ntfy_token`. Both are optional — absence is treated the same as the existing IFTTT optional config.

`seriesDir` and `movieDir` may independently be local paths or remote destinations. Example:

```json
"seriesDir": "david@nas:/volume1/plex/Anime",
"movieDir": "david@nas:/volume1/plex/Movies"
```

## Error Handling

| Scenario | Behaviour |
|---|---|
| rsync succeeds | Local file/dir deleted |
| rsync fails | Local file/dir left in place; ntfy notification sent (if configured); error logged |
| ntfy POST fails | Exception logged; does not raise |
| Either `ntfyUrl` or `ntfyToken` absent | Notification silently skipped |

## Testing

New file `test_remote.py`:

- **`test_is_remote`** — unit tests covering valid remote paths (`user@host:/path`) and local paths (absolute, relative, paths with `@` in the filename)
- **`test_rsync_success`** — mock `subprocess.run` returning exit code 0; assert local file is deleted
- **`test_rsync_failure`** — mock `subprocess.run` returning non-zero; assert local file is kept and ntfy `send_notification` is called
- **`test_ntfy_notification`** — skipped without `NTFY_CONTEXT` env var (same pattern as `test_notifications`); sends a real POST and checks HTTP 200
