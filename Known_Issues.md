# Nightjar Data Analysis Changelog

This Known Issues File records known issues to be addressed in future releases.

> Security note: credentials and passwords are intentionally excluded from this repository file. Store secrets in Railway environment variables or another secret store, never in source control.

## Known Issues

### From previous version

- The changes on the “Files” Tab do not show the contents of the EventData file or TestData File. Why?
- Shows in Edge but not in Chrome – weird. Do I need to clear Cache or something in chrome.
- Hide the Staysail, Staysail2, and Tank columns.
- Allow filtering by the columns.
- Doesn’t look like all the data are loading in. Why?
- By default have VMG% on in the settings.
- Why does the map always start zoomed out. Can it zoomed to the extents of the plot.
- Colour by tack doesn’t work consistently. It also draws straight lines between the tacks the opposite colour to the tack. Remove these lines
- Add colour scale limits to the Variable plot and map view colour scales.
- Move this to bottom of left hand panel. Separate each statement onto a new line
- Add ability to average y between 2 x values on variable plot.

### Immediate implement

- Correct error in reading in eventdata and testdata files
- Resolve error why no “Gun” entries are being found in the event data file and no rows past 500 ish (7th August) are loading.
- Rounding in tool tip (again)
- Display active variable also in tool tip on graphs.
- Change colour scheme for scale bars to be more high contrast.
- Allow adjustable limits on colour bar scale.
- Deal with BST Correctly.

### Performance

- Add ability to compute n th percentage polar based on available information and compare to the current polar.
- Use the same TWA as the current polar, and compute based on selected data. Allow user to choose the n’th percentile and also the tolerances on TWS and TWA that are included around each data point for the polar. Also include a cut off of x % above the calculated value and y % below it to remove any outlying data.
- Add variable plot and map in a side-by-side view on a new tab.

### File handling

- Add ability to upload new files, compare to the existing datafiles in the volume and append any new information in them (instead of having to upload whole new files to the volume).
- Also add for the website to check for updated files in the volume and reload data when they’re changed.
- Add ability to upload and save Ms word / google sheet debrief documents into the web page and view them.
- Add ability to create and store debrief notes in the website.
- Add ability to store rig information / to do list in the website.
- Can we link these files to a google drive folder?
- CHANGE THE PASSWORD.

### Later

- Would be good to implement a SQL database or similar to store the data instead of storing it as part of the memory.
- Also need to write up notes on how to change files I the railway volume.
- compare actual sailing data against target polars,
- edit polar curves,
- update sail selection charts,
- add notes/events,
- save analysis sessions and export useful outputs
