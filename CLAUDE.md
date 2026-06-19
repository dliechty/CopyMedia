# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

CopyMedia is a Python script that automates sorting downloaded media files into a Plex library. It is triggered by a torrent client (Deluge) after a download completes and:
1. Matches TV episode files against configured series using regex patterns
2. Renames and moves matched files into the correct series subdirectory under `seriesDir`
3. For unmatched files/directories, queries The Movie DB (TMDB) API to identify movies
4. Processes movie directories: finds the largest file, renames it `<title>.<year>.<ext>`, handles english subtitles (`.en.srt`), strips metadata via `ffmpeg`, and moves to `movieDir`
5. Optionally sends an IFTTT push notification on success
6. Optionally sends ntfy push notifications on success or failure (requires `-n`/`--ntfy-token` CLI arg and `ntfyUrl` in config)

## Running

```bash
# Run against a single file (typical torrent-trigger use)
python3 copy_files.py -f /path/to/file -c CopyMedia.json

# Run with Deluge's three args (torrent-id, torrent-name, torrent-path)
python3 copy_files.py <torrent-id> <torrent-name> <torrent-path>

# Scan entire download directory
python3 copy_files.py -s /mnt/downloads -d /mnt/plex/Anime -m /mnt/plex/Movies
```

## Tests

```bash
# Run all tests
python3 -m unittest test_copy_files.py

# Run a single test
python3 -m unittest test_copy_files.TestCopyMedia.test_find_largest_file
```

Two tests require environment variables and are skipped without them:
- `test_notifications` → set `IFTTT_CONTEXT` to the IFTTT trigger context/key
- `test_is_movie` → set `TMDB_CONTEXT` to the TMDB API key

The `test_rename_movie` test mutates `test_resources/` and then restores it — it is not safe to run in parallel.

## Dependencies

Dependencies live in `.venv/`. Activate with `source .venv/bin/activate`. The key third-party packages are:
- `PTN` (`parse-torrent-name`) — parses torrent file names into title/year/season/episode metadata
- `requests` — HTTP calls to TMDB API and IFTTT

`ffmpeg` must be available on `PATH` at runtime for metadata stripping.

## Configuration (`CopyMedia.json`)

Each series entry requires `name` (used as destination folder name) and `regex`. Optional fields:
- `destination` — override folder name if different from `name`
- `replace` — regex substitution string applied to the filename on copy (uses `re.sub`)
- `episode_num_sub` — integer subtracted from the episode number (for series where episode numbering restarts each season but the file names use absolute numbers)

## Code Architecture

All logic lives in `copy_files.py` as the `CopyMedia` class. The `__init__` method loads config and merges CLI args with JSON config (CLI takes precedence). The `execute()` method drives everything.

Supporting modules:
- `tmdb.py` — wraps TMDB REST API; `clean_name()` delegates parsing to `PTN` then post-processes titles to extract years ≥ 2020 (PTN v1.1.1 year regex only covers up to 2019); `is_movie()` returns `False` when no year is found (intentional — queries without year are unreliable)
- `ifttt.py` — single `send_notification()` call to IFTTT webhooks
- `ntfy.py` — single `send_notification()` call to ntfy; token supplied via CLI (`-n`/`--ntfy-token`), URL from config (`ntfyUrl`)
- `logger.py` — configures `logging` with a custom `TRACE` level (below `DEBUG`) and optional Cygwin path conversion
- `exceptions.py` — defines `ConfigurationError` raised for missing required config

## Custom Config File Fields (beyond README)

The `episode_num_sub` field is undocumented in the README but present in the code and tests. It handles shows like *That Time I Got Reincarnated as a Slime* where season 2 episodes are numbered 25+ in the torrent filename but should be stored as S02E01+.
