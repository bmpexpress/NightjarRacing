# Nightjar Data Analysis Changelog

This Known Issues File records known issues to be addressed in future releases.

> Security note: credentials and passwords are intentionally excluded from this repository file. Store secrets in Railway environment variables or another secret store, never in source control.

## Known Issues

### From previous version

- Add Summary of no. loaded points / lines from each file in left hand column at bottom. 
- Move the sign out box to top right of window.

### Immediate implement
- Move the "hide left hand pane" switch to top right also. 
- Add ability to average y between 2 x values on variable plot.
- Add in function to locate multiple races in a day using different "Gun" entries in event list
- Display active variable also in tool tip on graphs.

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

- CHANGE THE PASSWORD.

### Later

- Would be good to implement a SQL database or similar to store the data instead of storing it as part of the memory.
- Also need to write up notes on how to change files I the railway volume.
- compare actual sailing data against target polars,
- edit polar curves,
- update sail selection charts,
- add notes/events,
- save analysis sessions and export useful outputs
- Can we link these files to a google drive folder? Instead of a railway volume? 
