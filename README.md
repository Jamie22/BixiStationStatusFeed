# BIXI Station Status Feed

A Python script that tweets whenever a BIXI station is added, removed, or moved. This works by getting station data JSON from the BIXI API, and comparing with the previous version for changes. The JSON is stored on Pastebin so that it can be compared on the next iteration.

The script is running on Heroku on an hourly basis and posts at https://twitter.com/BIXIStatus

More info about BIXI: https://www.bixi.com/

The meaning of the tweets are explained below.

#### BIXI station permanently removed from x
The station has been removed and no longer appears on the map (https://secure.bixi.com/map/), suggesting it won't be reinstalled.

#### BIXI station moved from x to y
The station has been moved to a new location. On the map, the station will no longer appear at its old location

#### New BIXI station installed at x
A new station has been installed that did not previously appear on the map.

#### New BIXI station coming soon at x
A new station has appeared on the map, but is not yet installed. The pin is colored grey and says "Coming soon" when clicked on.

#### BIXI station installed at x
A station has been installed that was previously "Coming soon"

#### BIXI station removed from x
A station has been removed, but still appears on the map as "Coming soon"