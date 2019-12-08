# Copy Media
This is a small Python script to copy large file downloads to the correct folder and transform them on the way.

The general workflow is expected to be that a torrent is downloaded based on an auto-initiated RSS update, the video file lands in the destination folder, the torrent application auto-triggers the python script, and the video file ends up in the correct location within your media library.

The configuration file is a simple json structure, like so:
```json
{
    "scanDir":"D:\\Downloads",
    "moveDir": "Z:\\Shared Videos\\Anime",
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


Here is the usage text:

```
usage: copy-files.py [-h] [-f FILE] [-d DEST] [-s SCAN] [-c CONFIG] [-l LOG]
                     [-p PLEXLIBRARY]

Copy/transform large files.

optional arguments:
  -h, --help            show this help message and exit
  -f FILE, --file FILE  File to process. If not specified, then all files
                        within the scan directory are checked.
  -d DEST, --dest DEST  Destination parent directory
  -s SCAN, --scan SCAN  Directory to scan
  -c CONFIG, --config CONFIG
                        Configuration file
  -l LOG, --log LOG     Log file
```
