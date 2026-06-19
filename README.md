# Copy Media
This is a small Python script to copy large file downloads to the correct folder and transform them on the way.

The general workflow is expected to be that a torrent is downloaded based on an auto-initiated RSS update, the video file lands in the destination folder, the torrent application auto-triggers the python script, and the video file ends up in the correct location within your media library.

The configuration file is a simple json structure, like so:
```json
{
    "scanDir":"D:\\Downloads",
    "seriesDir": "Z:\\Shared Videos\\Anime",
    "movieDir": "Z:\\Shared Videos\\Movies",
    "ntfyUrl": "https://ntfy.sh/your-topic",
    "series": [
        {
            "name": "One-Punch Man",
            "destination":"One Punch Man",
            "regex": "(.*)(One-Punch Man)( - )(\\d{1,})(.*)"
        },
        {
            "name": "Goblin Slayer",
            "regex": "(.*)(Goblin Slayer)( - )(\\d{1,})(.*)"
        },
        {
            "name": "In Another World With My Smartphone",
            "regex": "(.*)(Isekai wa Smartphone to Tomo ni.)( - )(\\d{1,})(.*)",
            "replace": "\\1In Another World With My Smartphone\\3\\4\\5"
        }
    ]
}
```

Possible top-level config fields are:
- `scanDir` : directory to scan for new downloads
- `seriesDir` : destination root for TV series. May be a local path or a remote rsync destination in the form `user@host:/path`
- `movieDir` : destination root for movies. May be a local path or a remote rsync destination in the form `user@host:/path`
- `ntfyUrl` : (optional) full URL to an [ntfy](https://ntfy.sh) topic, e.g. `https://ntfy.sh/your-topic`. Used to send push notifications on success or failure.

Possible series tags are:
- `name` : the name of the series, as well as the default destination folder name if not specified by `destination`
- `destination` : the name of the destination folder, if different from `name`
- `regex` : the pattern that is used to match the file name
- `replace` : the pattern used to transform the file name when it is copied to the destination

### Remote destinations (Synology NAS / rsync)

`seriesDir` and `movieDir` can each be a remote destination in the form `user@host:/path`:

```json
{
    "seriesDir": "david@nas:/volume1/plex/Anime",
    "movieDir": "david@nas:/volume1/plex/Movies"
}
```

When a remote destination is configured, files are transferred using `rsync` over SSH instead of a local move. The local copy is deleted after a successful transfer. If the transfer fails, the local copy is kept and a push notification is sent via ntfy (if configured).

Requirements:
- `rsync` 3.2.3+ must be available on `PATH` (for `--mkpath` support)
- The SSH key for the remote host must already be trusted (no password prompt)

If a file is not found within your defined series, then a query can be made against the movie database API to determine if the file is a movie. If so, the file can be moved to a designated movie directory instead. This functionality relies on the parse-torrent-name library available here: https://github.com/divijbindlish/parse-torrent-name

Here is the usage text:

```
usage: copy_files.py [-h] [-f FILE] [-d DEST] [-m MOVIEDEST] [-s SCAN] [-i IFTTT] [-c CONFIG] [-t TMDB] [-n NTFY_TOKEN] [-l LOG] [delugeArgs [delugeArgs ...]]

Copy/transform large files.

positional arguments:
  delugeArgs            If deluge is used, there will be three args, in this order: Torrent Id, Torrent Name, and Torrent Path

optional arguments:
  -h, --help            show this help message and exit
  -f FILE, --file FILE  File to process. If not specified, then all files within the scan directory are checked.
  -d DEST, --dest DEST  Destination directory for series
  -m MOVIEDEST, --moviedest MOVIEDEST
                        Destination directory for movies
  -s SCAN, --scan SCAN  Directory to scan
  -i IFTTT, --ifttt IFTTT
                        IFTTT trigger URL context and API key
  -c CONFIG, --config CONFIG
                        Configuration file
  -t TMDB, --tmdb TMDB  The Movie DB API key
  -n NTFY_TOKEN, --ntfy-token NTFY_TOKEN
                        ntfy access token
  -l LOG, --log LOG     Log file
```
