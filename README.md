## Collection Tracker

- The website will dynamically generate a table from a CSV file.
- The "done" column determines whether or not you've completed that game. The table will dim these entries.
- Instances of "[hd]" in the CSV get parsed and displayed as an image, you can label remakes/remasters this way.
- It checks builds.csv for appid and buildid values and informs you if there's an update available on steam.

I made this tracker for personal use, as I felt it was unnecessarily complicated to maintain collections with tons of metadata and lots of forms to fill in existing websites made for this purpose. Editing a text file with only half a dozen fields per game is simple and easy for me, but I then wanted the output to be pleasant and accessible online.

You can fork this project and just edit the CSV through Excel or just a text editor if you understand the file structure. I guess a goal for the future would be to add the ability to maintain the list entirely within the website, without the need for manual file editing.
