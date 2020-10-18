## BIXI Station Status Feed

A Python script that tweets whenever a BIXI station is added, removed, or moved. This works by getting station data JSON from the BIXI API, and comparing with the previous version for changes. The JSON is stored on Pastebin so that it can be compared on the next iteration.

The script is running on Heroku on an hourly basis and posts at https://twitter.com/BIXIStatus

More info about BIXI: https://www.bixi.com/