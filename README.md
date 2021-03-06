# Copy Media
This is a small Python script to copy large file downloads to the correct folder and transform them on the way.

The general workflow is expected to be that a torrent is downloaded based on an auto-initiated RSS update, the video file lands in the destination folder, the torrent application auto-triggers the python script, and the video file ends up in the correct location within your media library.

The configuration file is a simple json structure, like so:
```json
{
    "scanDir":"D:\\Downloads",
    "seriesDir": "Z:\\Shared Videos\\Anime",
    "movieDir": "Z:\\Shared Videos\\Movies",
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

Possible tags are:
- `name` : the name of the series, as well as the default destination folder name if not specified by 'destination'
- `destination` : the name of the destination folder, if different from `name`.
- `regex` : the pattern that is used to match the file name
- `replace` : the pattern used to transform the file name when it is copied to the destination

If a file is not found within your defined series, then a query can be made against the movie database API to determine if the file is a movie. If so, the file can be moved to a designated movie directory instead. This functionality relies on the parse-torrent-name library available here: https://github.com/divijbindlish/parse-torrent-name

Here is the usage text:

```
usage: copy_files.py [-h] [-f FILE] [-d DEST] [-m MOVIEDEST] [-s SCAN] [-i IFTTT] [-c CONFIG] [-t TMDB] [-l LOG] [delugeArgs [delugeArgs ...]]

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
  -l LOG, --log LOG     Log file
```
