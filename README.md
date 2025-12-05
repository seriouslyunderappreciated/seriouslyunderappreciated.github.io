## Collection Tracker

- The website will dynamically generate a table from **collection.csv**.
- It will check for updates for anything you plug into **builds.csv**.
- You can display what you're playing at the moment by editing **atm.txt**.

Games marked as "done" (`Yes` in `done` column) will appear dimmed in the table.
Updates are checked by looking at the build id stored in the relevant csv file, then using SteamCMD to look at the latest public branch for that appid.
If you insert `[retro]` or `[switch]` in an entry in the collection csv, the website will show a corresponding icon. I use this to signify that a game I have in a particular device was not originally made for that device, in this case being emulated via retroarch or played via backwards compatibility on the Switch 2.
