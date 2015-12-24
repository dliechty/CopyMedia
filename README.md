# Copy-Anime
This is a small Python script to copy/transform large file downloads and auto-trigger a folder scan in the plex media server to the correct folder.

The general workflow is expected to be that a torrent is downloaded based on an auto-initiated RSS update, the video file lands in the destination folder, the torrent application auto-triggers the python script, and then the video file ends up in the correct location within your plex library, and the plex software has had a chance to index it.

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
            "name": "Gakusen Toshi Asterisk",
            "regex": "(.*)(Gakusen Toshi Asterisk)( - )(\\d{1,})(.*)"
        },
        {
            "name": "Taimadou Gakuen 35 Shiken Shoutai",
            "regex": "(.*)(Taimadou Gakuen 35 Shiken Shoutai)( - )(\\d{1,})(.*)",
            "replace": "\\1\\2\\3S01E\\4\\5"
        }
    ]
}
```

Possible tags are:
- name : the name of the series, as well as the default destination folder name if not specified by 'destination'
- destination : the name of the destination folder.
- regex : the pattern that is used to match the file name
- replace : the pattern to use to transform the file name when it is copied to the destination
