# Nightjar Data Analysis Changelog

### 0.10.1 - Volume-backed data and event management

#### Changes implemented
- Replaced the resident full-log cache with a persistent DuckDB catalogue and compressed Parquet files under `/Data/.nightjar_store`. CSV/sparse ingestion writes bounded chunks instead of concatenating a master DataFrame.
- Date, event, GUN-minus-five-minute and time-trim predicates run in SQL before selected page columns are fetched. Map and variable selectors use schema metadata, so selecting a channel does not require loading every numeric column.
- Connections close after each query. There are no global DataFrame caches. Session-scoped temporary-file handles are released on disconnect; sign-out clears the current session. Garbage collection and best-effort Linux allocator trimming run after each script execution. Persistent master data is not deleted by session cleanup.
- Settings includes Add event: required logfile, date, Inshore/Offshore type and name, with optional revised EventData, TestData and polar. Successful imports publish a complete new snapshot atomically. EventData/TestData merge by exact row; a revised polar replaces the active polar. Exact duplicate logfiles are rejected; overlapping records in different files are retained, not silently deduplicated.
- New full-master, sidebar-filtered and current-tab download preparation. Exports use Excel-date Utc values and the unchanged source log clock. Native sparse exports reuse source channel IDs; channels without source IDs are omitted from that format. Extracted CSV retains available native columns. Existing filtered CSV and session-settings exports remain, with large CSV preparation made explicit rather than allocating it on every rerun.
- EventData/TestData viewers and the Map View event table filter by selected event dates, or the date range when no events are selected. Event times are interpreted as UTC and converted to the selected log clock for date matching; displayed source cells remain unchanged. GUN/time trimming does not hide the event metadata itself.
- Empty and constant channels are physically excluded from working Parquet and the working database view. Settings reports each discarded variable and reason. Classification covers the entire accumulated master, not just a selected event. A timestamp key is retained; a non-empty value with missing gaps is not classified as constant. Small scalar metadata can supply constant inputs to derived calculations without restoring a stored working column.
- Original inputs and unpruned archival Parquet remain available for complete exports and reclassification. A later upload can reactivate a previously discarded channel. Original root files are not overwritten: the active master and merged reference files live in the snapshot selected by `.nightjar_store/CURRENT`.
- Existing root reference-file changes are detected by file signature. A changed original master logfile is reported as a conflict rather than silently replacing accumulated imports. Sidebar uploads remain session-only overrides; adding to the persistent master is disabled while a sidebar log override is active.
- Existing styling, navigation, authentication, plotting/calculation routines, units, tack colours and full-resolution behaviour remain. Event-list CSV parsing now handles quoted names containing commas.

#### Dependencies and deployment
- Streamlit minimum raised to 1.53 for session-scoped resource release; added DuckDB and PyArrow. Other existing dependency ranges retained. PyArrow is constrained to the tested 19.x series.
- Existing Railway start command and theme configuration are unchanged. `config.txt` supplied in this session represents `.streamlit/config.toml`.
- Default data directory remains `/Data`; optional `NIGHTJAR_DATA_DIR` supports another mounted directory/local testing. DuckDB defaults to a 256MB buffer budget and two threads, configurable through `NIGHTJAR_DB_MEMORY_LIMIT` and `NIGHTJAR_DB_THREADS`. This is not a cap on total Python, download or browser memory.

#### Checks actually performed
- Python syntax compilation passed.
- Storage fixtures passed: 12,007-row/two-chunk ingestion, projected SQL selection, persistence/reopen, append, duplicate rejection, discarded-channel reactivation, blank/gapped-channel classification and physical working-schema pruning.
- Extracted CSV and source-ID sparse export round-trips passed through the application parser, including own-boat filtering and a channel appearing in a later sparse section.
- SQL GUN filtering matched the existing pandas implementation on summer, winter and both 2026 UK DST-transition dates. Viewer date-boundary filtering passed.
- Sidecar merge, polar replacement, root reference-file refresh, invalid-polar rollback, malformed-CSV rollback and session-directory cleanup passed. Constant scalar inputs remained usable for derived VMG percentage calculations.
- Streamlit AppTest rendered all eight pages without exceptions. Projected map/variable selection changes, three export preparation scopes, appended-event selection, sign-out and empty-selection page runs passed.
- AST comparison confirmed 55 existing functions/classes unchanged; CSS, column aliases and default filenames were unchanged.
- Tests used constructed fixtures, not supplied sailing logs. Tested runtime: Python 3.12.15, Streamlit 1.53.1, DuckDB 1.5.6, PyArrow 19.0.1, pandas 2.2.2, NumPy 1.26.4 and Plotly 6.5.0.

#### Limits and manual acceptance
- No Railway deployment, real-browser disconnect test, production memory measurement or import into Expedition was performed. No numerical memory-saving claim is made.
- Session data is not globally cached, but Streamlit upload/download/chart buffers and native allocators can retain memory until released. Browser closure is not an immediate zero-RAM guarantee. Large selected datasets and prepared downloads still need RAM.
- Sparse export omits channels lacking source IDs. Current-tab export is the tab's processed native-channel dataset, including averaging where applied; display-only absolute-value/label columns and axis limits are not additional export filters. Native Expedition import remains a manual acceptance check.
- Event association remains date-based, including the existing first-GUN-per-day behaviour. Separate same-day race windows and multi-day event redesign were not introduced.
- Snapshots and raw inputs consume volume space. Previous snapshots are retained for recovery; automated retention/compaction is not included. Single-volume operation is the tested model; multi-replica/network-filesystem operation is unverified.
- Full installation, manual test and rollback guidance is in the accompanying release notes. Newly imported events are not automatically visible to the old 0.10.0 app because it reads the original root files.


## 0.10.0 - Streamlit update from accepted 0.8.1 baseline

The uploaded app.py is the accepted 0.8.1 baseline; its old 0.8.0 version declaration was stale. This release remains Python/Streamlit and does not reintroduce the Java migration.

### Changes implemented
1. Automatic date-specific BST/GMT correction for UTC GUN times when trimming UK-local logs. The five-minute lead-in is subtracted in UTC before timezone conversion. Settings includes a UTC log-clock option to avoid double correction for UTC logs. Source EventData remains unchanged.
2. Removed loading-time record thinning, plot downsampling, point caps, application RAM budgets and the CSV download memory-size restriction. Chunked parsing and dtype optimisation remain, but retain every valid own-boat record. Old sampled Parquet caches are not reused.
3. Added a Show event sidebar toggle in the main area; event selection remains in the sidebar and is preserved when hidden.
4. Moved column mapping to Settings. The former performance-mode and point-limit controls are removed, not re-enabled; Settings explains full-resolution plotting. Single-active-page rendering remains.
5. Event/tack colour controls are visible on plot pages. Port/negative signed TWA is red; starboard/positive signed TWA is green. Event colouring is enabled when multiple events are selected. Sail-chart polygons retain their sail colours; an optional actual-data overlay supplies event/tack colouring.
6. Variable plots automatically label Cartesian axes with selected variable names, and label radial/angular variables in polar mode.
7. Renamed GPS track navigation to Map View.
8. Settings lists all loaded Expedition variables, enabled by default, with select-all/select-none and individual inclusion. Exclusions affect selectable plot channels and Overview channels, not stored data, calculations or exports. Fixed map/polar coordinates remain available. Mapping and variable choices persist across page navigation within the session.
9. Added File viewer for complete EventData and TestData tables from uploads or /Data. The viewer does not apply event filters or truncate at 500 rows, and can operate without a master log.

### Dependencies
- Retained the original Streamlit, pandas, NumPy and Plotly version ranges.
- Explicitly declared tzdata for timezone availability and python-docx for the existing DOCX debrief reader.

### Verification and limits
- Python syntax compilation and 50 targeted checks passed using constructed test fixtures, not actual sailing data.
- Checks cover summer/winter and DST transitions, GUN-minus-five-minute boundaries, full record retention, VMG preservation, polar point counts, tack colours, page execution, settings persistence, variable exclusions and 601-row file viewing.
- Streamlit AppTest used a table-rendering substitute because the sandbox Arrow/NumPy installation is incompatible. Table preparation was tested; actual Arrow table rendering, browser appearance and Railway deployment were not verified.
- Full-resolution plotting can exhaust actual server/browser resources; removing application limits does not increase provisioned capacity.
- Naive timestamps do not identify their timezone. UK-local log time is the default assumption; select UTC in Settings for UTC logs. GUN source times are assumed UTC.

## Historical development notes

Historical requests and future ideas below are retained as history, not claims of implementation in 0.10.0. Text was recovered from the previously supplied Changelog.docx; embedded screenshots are not reproduced.


## 20260821 – MVP Rev0.1


## Notes.

- Version runs well, once I got my head around the mapping.
- Saved app app_0.1.py

## Requested updated for Rev0.2

- In GPS track tab:
- round off the time to the nearest second.
- Display the heel as a tooltip point.
- Display VMG as a tooltip point.
- Display Tide rate (Drift) as a tooltip point.
- Colour by VMG instead of BSP.
- In the overview Tab:
- Add VMG Values to the overview plot.
- In the Polar analysis Tab:
- Change values on the starboard tack to be negative values, instead of > 180 degrees.
- Add ability to show all data, or to show just for a given wind range, with a given “bin” above and below.
- Add ability to display data on a full polar plot or on a ½ plot (i.e. using abs values)
- The legend clashes with the figure title.
- Also make the radial values (boat speed) in bold and ontop of all data so it is clearer to see.
- In the tool tip also display the awa.
- In th sail crossover chart, close all of the shapes plotted, also respect the colours and shading in the xml file, can you import it directly into the web page? If not, then use plotly to recreate it.
- Add a “Variable plot” Tab, that allows you to plot any variables from the log file against each other.
- Also allow you to filter by true wind speed +- a tolerance to give a “bin” of data.
- Display the logo top right of the screen.

## 20260821 – App_0.2.py

- Requested the changes above.

## Updates requested

- Move “point of sail” selection  from sidebar into the polar plotting tab.
- In the “polar Analysis” tab. Match the bin center to the selected polar speed automatically.
- Change VMG plot on the gps track to plot by VMG (value) NOT VMG percentage, so we can view it independent of the polar.
- In the variable plot tab. Add an option to plot “abs” values of each value. Also add an options to produce a polar plot instead of cartesian.
- In the overview tab also plot the twa.

## 20260821 – App_0.3.py


## Review

- VMG Channel missing from overview plot.
- Note that in the polar plot they are single data points with no time averaging

## Requested changes

- In GPS track page,
- remove “nearest second” from the tool tip description for time.
- be able to choose to colour by bsp or VMG, or other variables.
- Add adjusting the limits of the colour scaling
- In the variable plot tab:
- Add the ability to choose the colour scaling limits for the plot.
- In the polar plotting tab,
- choose to plot in cartesian or polar space. Also choose the y axis limits.
- add in time averaging (so data is averaged over “n” seconds). Also include adjustable cutoffs for variation in TWS and BSP during the averaging window.
- the “half polar” plots from -90 to 90. Change this to 0 to 180.

## 20260822 – App_0.4


## Comments


## Changes requested

- Changes to the appearance of the page:
- Move Nightjar logo into top of sidebar top left.
- Reduce the header space above the tabs to maximise usable on screen space.
- When a box is ticked or tab selected instead of red change colour to orange instead.
- When the mosue hover
- Add a time filter option for the data in the left pane as well as date filtering so you can choose the data to display by time window as well as date.
- In the gps track:
- match the data plot to the time average in the polar analysis tab.
- As well as the dots, show a line along the boat’s track.
- Add in an absolute value button for the data used for scaling (e.g. so that heel displays only from 0 upwards)
- In the Variable Plot:
- Also add time averaging with tolerances on variable magnitudes changing during the averaging window.

## 20260822 – App_0.5, 0.5.1, 0.5.2,0.5.3,0.5.4


## Notes / bug fixes

- ERROR IN POLAR PLOT PAGE. – Due to two widgets (check boxes) having the same name - Resolved in 0.5.1 version by giving unique ID to each instead.
- ERROR in GPS Track page, Map data not showing – Due to style error in mapbox – Resolved in 0.5.2 verison.
- Error in GPS track page, points with nan data plotting as part of the track:
- Fixed in 0.5.3 version.
- Appearance not correct:
- When hovering over text it should appear orange not red.
- All of the selected buttons / tick boxes should be orange not red too.
- Also Polar plot being incorrect when ½ plotted only.
- Fixed in 0.5.4, 0.5.5 version.

### 0.5.5 still plotting this wrong.

- In 0.5.6 the nan data plotting error has come back. Solved previously in version 0.5.3. Ask to re-fix in next version.

## Changes for next version

- Filter events by offshore/inshore, a column has been added to the event list file for this.
- Multi select events in the filter tab.
- Summary tab with summary of each event.
- Sort by TWS, provide upwind and downwind TWA, AWA, BSP, VMG, VMG%. For each polar windspeed.
- Start Info: move from in GPS tab. Display “GUN” data in event summary tab for each event.
- Upload the defbrief notes and have viewable.
- Rotate and mirror half polar so zero is at the top and it goes clockwise.
- Using the “Event” file from expedition, if there is a “gun” type entry, use this as the start time for the days racing. Filter out all data up until 5 minutes before the “gun” entry. If there is no “gun” entry, notify the user and tell them to filter by the times manually.
- Change the loading window so it’s a bar across the top.
- Change the header so they’re slightly lower, currently they’re covered by the page top bar with “deploy” on it.
- VMG does not automatically map to “VMG” from expedition, please make it so this happens automatically.
- In the GPS page, add “AWA” to the tool tip info.

## 20260822 – 0.6.0


## Bug fix versions


### 0.6.0 Notes

- Still doesn’t automatically map VMG
- AWA in the event summary is incorrect in some cells, looks like the averaging is incorrect.
- Make sure all fill / linework is in Nightjar orange as defined in the html.
- Data from other boats are plotting. In the log file import it needs to ignore all data entries that are not “0” in the “Boat” column of the load file
- Round off all values to 2 DP max.
- Event type interpretation is wrong: . In the event list file the format is [Date],[Event Type],[Event Name]. The start times are no longer saved. They’re identified from the “Gun” expedition event file entry.
- Implementing above for 0.6.1.

### 0.6.1

- Remove the loading bar.
- Change these from red to orange:
- - Hovering over text.
- - The fill in these boxes
- - This warning box.
- Move this header to the Top of the left Pane, so there is more useable space in the interface:

## 0.6.2

- Above changes implemented.
- For next version, resolve:
- For `use_container_width=True`, use `width='stretch'`. For `use_container_width=False`, use `width='content'`.
- C:\Users\Bryn.Phillips\OneDrive - Ward and Burke\Documents\99. MISC personal\Sailing\2026 - Nightjar\Website\20260821 - MVP\app_0.6.2.py:821: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
- session = {"version":APP_VERSION, "created_utc":datetime.utcnow().isoformat()+"Z", "rows":len(filtered), "mapping":m}
- 2026-08-22 11:43:07.804 Please replace `use_container_width` with `width`.
- `use_container_width` will be removed after 2025-12-31.
- Time avg causes float error still
- AttributeError: 'NotImplementedType' object has no attribute '_indexed_same'
- Traceback:
- File "C:\Users\Bryn.Phillips\OneDrive - Ward and Burke\Documents\99. MISC personal\Sailing\2026 - Nightjar\Website\20260821 - MVP\app_0.6.2.py", line 823, in <module>
- if __name__ == "__main__": main()
- ~~~~^^
- File "C:\Users\Bryn.Phillips\OneDrive - Ward and Burke\Documents\99. MISC personal\Sailing\2026 - Nightjar\Website\20260821 - MVP\app_0.6.2.py", line 791, in main
- vd, avg_note = average_with_ranges(filtered, ts, avg_columns, int(vavg), tolerances, signed_twa_col=x if x==twa else None)
- ~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
- File "C:\Users\Bryn.Phillips\OneDrive - Ward and Burke\Documents\99. MISC personal\Sailing\2026 - Nightjar\Website\20260821 - MVP\app_0.6.2.py", line 314, in average_with_ranges
- if col in ranges and tol is not None: keep &= ranges[col] <= tol
- ^^^^^^^^^^^^^^^^^^^^^^^^^^
- File "C:\Users\Bryn.Phillips\.conda\envs\Streamlitenv\Lib\site-packages\pandas\core\generic.py", line 12823, in __iand__
- return self._inplace_method(other, type(self).__and__)  # type: ignore[operator]
- ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^
- File "C:\Users\Bryn.Phillips\.conda\envs\Streamlitenv\Lib\site-packages\pandas\core\generic.py", line 12758, in _inplace_method
- and result._indexed_same(self)
- ^^^^^^^^^^^^^^^^^^^^
- GPS page auto scale function – add a button that automatically scales the colouring by the max and min values. Also add to the other graph pages.

## 0.6.3

- Happy with the 0.6.n version now. Changing to 0.7 as going to make a more major change to try and improve the speed of the website.

## Changes for 0.7

- Changed to “0_Master log file” as the log file. 230 MB Data.
- Takes a long time to load data now. This file is very large, I wonder if there is a more efficient way to store / use the data.
- OUTPUT:
- Missing – why.
- Needs to scale by the currently selected data, not just vmg.

## 0.7.1


### Notes

- Implemented above – Now resolved.

### Changes to make

- If VMG not logged, then get the app to calculate VMG and store.
- Do not use VMC, this is a different measurement.
- Calculate VMG from BSP and TWA when loading the data in.
- Polar analysis page. Also show the VMG and wind speed in the tool tip
- Resolve this error:
- DeprecationWarning: *scattermapbox* is deprecated! Use *scattermap* instead. Learn more at: https://plotly.com/python/mapbox-to-maplibre/     fig.add_trace(go.Scattermapbox(
- Resolve this error:
- DeprecationWarning: The 'generic' unit for NumPy timedelta is deprecated, and will raise an error in the future. This includes implicit conversion of bare integers (e.g. `+ 1`).Please use a specific unit instead.
- start_time = gun_time - pd.Timedelta(minutes=5)
- Add a password page that you have to put in before you can view the main website.
- How is best to do this?

## 0.7.2


### Notes

- Changes implemented and password set to [REDACTED]

### Changes to make

- Instead of having a “Calculated_VMG” just insert the calculated values into the “VMG” column for data.
- Change folder structure so the data is contained in a “/data” sub folder instead of with the app.

## 0.7.3


### Notes

- Hopefully deployment version.

### Changes to make

- The VMG percentage (VMG_PCT) is now not showing. Ensure this value is calculated if missing using the uploaded polar file and available to plot.

## 0.7.4


### Notes

- Changes made above.
- Need to be careful now about version control.

### Deployment

- Code now on Github.
- Note that app is just called “app.py” now. Version is saved within the file as an “App Version” info.
- Deployed onto Railway.
- Website forwards to Railway webpage for data.
- Password protected, [REDACTED].
- BP TO ADD NOTES ON DATA UPLOAD.

### Changes

- Change name from “Nightjar Polar analysis” to “Nightjar Data Analysis”.
- Sort out the data storage in Railway so it loads automatically.
- Change to run more efficiently with memory

## 0.7.5


### Notes

- Changes implemented, still not running due to out of memory error. Will need to run much more efficiently.
- Changing the “logfile” by running a pre-processing script on it to remove excess columns.
- Running the cleaner on the file reduced its size from 230 MB to 178 MB. Will try uploading now and see if the website will run.
- App still has the memory error so:
- I will change the script to load the data in chunks, so that it doesn’t exceed the memory limits.

## 0.7.6


### Notes.

- Changed so that input is read 25000 rows at a time to reduce memory useage.
- I think this is now working. Memory useage is still high.
- Lulu is now working on the site as a beta tester. She will identify any issues.

### Changes to make

- Also the memory useage is still high. I think the app is creating too many copies of variables and has large cache’s of information for the GPS plot page etc.
- Need to move so time filter and event filter come above variable mapping.
- Row 1104 defines the start time, unsure what the default value is / why 09:20 is always selected. Set this to 00:00 and end_t to 23:59
- Can you add current ram usage as a note?
- Remove “log Ram” from sidebar.

## 0.7.7


### Notes

- Above changes requested.

### Changes

- Move event filtering above file uploads.
- Add explainer under “performance mode” toggle explaining limits to max 10,000 points in any given figure.
- Make the memory readout box smaller, also make it in the nightjar colour scheme.
- Make the click behaviour of the tab selection buttons on the top menu so you can click anywhere.

## 0.7.8


### Notes

- Above changes implemented.

### 0.7.8.1 Verison – Error Fix in code.


### Changes

- Move event filters above input files in side bar.
- Remove the orange boxes around the headers and change back to tabs with a separator underneath to make more clear.
- The filtering by inshore and offshore doesn’t narrow down the events list.
- Add a header above the start time and end time selectors in the left menu with “Trim Data” as the title. Then add a toggle that selects whether to trim the data or not. If it is not selected then display all the data (excluding any before the “gun” log entry as already built in).
- When multiple events are selected, can you add a toggle switch on all plotting pages that is “Colour by event” then colour the data by the event that data is from instead of the colour variable.
- In the variable plot chart, when you change the plotted variables, don’t automatically update the chart axis limits.

## 0.7.9


### Notes


### Changes

- Move the no GUN warning message in the left hand bar to below the trim data section.
- Change logo to PNG file with no background.
- No words under logo.
- Instead of click buttons for the top menu selectors, make it Tabs that you click and the outside of the box goes orange when selected.
- On the Login Page, center all of the text instead of left align.
- Add in the Nightjar logo.jpg above the “Nightjar Data Analysis” Header.
- Change the logo file type from jpg to png.

### Notes

- Changes above implemented.
- Various minor revisions to sort colouring and minor UI changes.
- Can’t get text on login page to center align.

## UPDATES ONCE OPERATIONAL


## 8.1.0


### Notes

- Trying to improve memory efficiency.
- Added colour by tack option.
- Round of to 4 sig figs in tool tips

### Changes

- Note that up until this version the custom start command on railway was:
- python -m streamlit run app.py --server.address=0.0.0.0 --server.port=8080 --server.headless=true --browser.gatherUsageStats=false
- This has now changed with the Java deployment.

## Change to Java from Streamlit


## 0.9.0


### 0.9.0 Objectives

- Uprev the version number of the code to 0.9.0
- Change from Stream-lit deployment to a Java deployment, more in common with other websites.
- Automatically correct for BST in data, when the “gun” time that data are cropped by is in UTC. Currently it is removing the first hour of events.
- Make the styles and formatting more consistent with the Nightjar colour scheme.
- Include a line that separates the tabs at the top of the website from the content below.
- On the settings tab, add a list of all the variables and then allow the user to remove them from calculation / displaying on the website.
- On the variable plot tab, allow the x of y axis variable to be time.
- For all filters, change the default values to 1 from 99.
- On the GPS plot page, round off the gps time to the nearest second. Also do this wherever time is shown.
- Remove the down sampling of data and restrictions on memory usage as I now have access to more memory.
- Note Possible start command required: java $JAVA_OPTS -jar /app/app.jar
- Note – Multiple 0.9.0.x revisions to try and fix bugs in the new code.
- Current implementation online uses a massive amount of computer memory (13 GB). Why is this. How can this be reduced? Memory usage is also high on Railway at 2.5 GB, it used to be < 1 GB, why? The website is also slow now.
- Website is working slowly now with Java. But changing to 0.9.1 to make the memory efficiencies.

### Changes for 0.9.1

- Improve memory efficiency.

## 0.9.1


### Notes

- Failed on first build. Going through minor changes.
- Dockerfile updated. Now working.
- Sail select wasn’t loading and eventdata wasn’t loading. Also fixed.

### Changes

- Build back in changes that have been lost from below!

## 0.9.2


### Notes

- Java version now working. Now trying to re-implement the lost functionality.
- Requests:
- General:
- Change the script to reload the Nightjar logo into the top left of the main page.
- Also have it in at the top center of the password page.
- Colour scheme is now all orange. Change back to the blue colour scheme from Streamlit versions with only selected items being orange.
- Add back in filter by inshore or offshore when selecting events.
- Move the Event selection to the top of the left hand panel. With the input files section below it.
- On all pages with plots:
- Add “colour by tack” option back to polar, variable plotting, and gps page.
- Add “Colour by event” option back to above pages.
- Add a time averaging to the plots on each page. Within the time averaging allow the user to select a maximum variation in the plotted variables
- Change default colour scales in all plots to blue to red, not white to red as at present.
- Polar Plot:
- Half polar view plotting from -90 to 90, should plot 0 to 180.
- Add selection to show full polar plot (so showing both tacks) or showing ½ polar (plotting abs(twa)) also have an option to plot in cartesian space.
- gps Plot:
- always show in the tooltip: TWS, TWA, BSP, Heel, as well as the value of the variables being plotted.
- Settings Page:
- Move “save settings” button to top of page.

### Changes

- General:
- Remove sign out button from left hand pane.
- Make left hand panel hide-able
- Change Style to dark blue background with light text.
- Use orange for selected values.
- For the plots colouring by tack or event, make these switches on the page instead of a drop down selection. Enforce when 1 is switched on the other is switched off (if it is on).
- Figure downsampling warning:
- Add note to say where to turn off.
- Update it to the actual number of samples.
- Remove the “sign out” box from top right.
- Polar Page:
- Half polar still plotting -90 to 90. Plot 0 to 90.
- When doing full polar plot target polar on both sides.
- Sail Selection Page:
- Plot from 0 to 180 deg.
- Add option for catesian plotting.
- Variable Plot:
- Add axis labels.
- Add option to plot absolute values only.
- Add text box option to set axis limits.
- GPS Page:
- Start with the plot zoomed to the extents of the data only.
- Settings page:
- Add an option for selecting variable to “Select only used” set it to this by default.

## 0.9.3


### Notes

- Now working. New workflow for updating working well.

### Changes

- Add scale bars to the sides of plots in the Map View, Variable Plot, and Polar Plot tabs.
- Change the plot background to a darker colour that matches the site style, or make it transparent.
- When “Colour by tack” is selected, display port tack (negative TWA) in red and starboard tack (positive TWA) in green.
- Move the Hide Panel / Show Panel button so it is inline with the tab selection.
- Rename the “GPS” tab to “Map View”.
- Map the VMG_PCT variable from VMG% by default.
- In the “Files” tab, add a window allowing the user to view either EventData or TestData from Expedition for the filtered events.

## 0.9.4


### Notes

- Working well

### 0.9.4.1 Minor revision to fix issues.


## 0.9.5 – File Structure Change.


### Info:

- File structure now:
- nightjar-data-analysis-0.9.5/
- ├── CHANGELOG.md
- ├── README.md
- ├── pom.xml
- └── src/
- └── main/
- ├── java/
- │   └── com/
- │       └── nightjar/
- │           └── analysis/
- │               ├── NightjarApplication.java
- │               └── WebController.java
- └── resources/
- ├── application.properties
- └── static/
- ├── index.html
- ├── styles.css
- ├── js/
- │   ├── app.js
- │   ├── api.js
- │   ├── state.js
- │   ├── common.js
- │   ├── overview.js
- │   ├── polar.js
- │   ├── sail-selection.js
- │   ├── map-view.js
- │   ├── variable-plot.js
- │   ├── files.js
- │   └── settings.js
- └── pages/
- ├── header.html
- ├── sidebar.html
- ├── overview.html
- ├── polar.html
- ├── sail-selection.html
- ├── map-view.html
- ├── variable-plot.html
- ├── files.html
- └── settings.html

### 0.9.5.1

- First version didn’t load.

### 0.9.5.2

- 2nd version also didn’t load.

## FUTURE

- The changes on the “Files” Tab do not show the contents of the EventData file or TestData File. Why?
- Shows in Edge but not in Chrome – weird. Do I need to clear Cache or something in chrome.
- Hide the Staysail, Staysail2, and Tank columns.
- Allow filtering by the columns.
- Doesn’t look like all the data are loading in. Why?
- By default have VMG% on in the settings.
- Why does the map always start zoomed out. Can it zoomed to the extents of the plot.
- Colour by tack doesn’t work consistently. It also draws straight lines between the tacks the opposite colour to the tack. Remove these lines
- Add colour scale limits to the Variable plot and map view colour scales.
- Move this to bottom of left hand panel. Separate each statement onto a new line:
- Add ability to average y between 2 x values on variable plot.
- Immediate:
- Correct error in reading in eventdata and testdata files
- Resolve error why no “Gun” entries are being found in the event data file and no rows past 500 ish (7th August) are loading.
- Rounding in tool tip (again)
- Display active variable also in tool tip on graphs.
- Change colour scheme for scale bars to be more high contrast.
- Allow adjustable limits on colour bar scale.
- Deal with BST Correctly.
- Performance:
- Add ability to compute n th percentage polar based on available information and compare to the current polar.
- Use the same TWA as the current polar, and compute based on selected data. Allow user to choose the n’th percentile and also the tolerances on TWS and TWA that are included around each data point for the polar. Also include a cut off of x % above the calculated value and y % below it to remove any outlying data.
- Add variable plot and map in a side-by-side view on a new tab.
- File handling:
- Add ability to upload new files, compare to the existing datafiles in the volume and append any new information in them (instead of having to upload whole new files to the volume).
- Also add for the website to check for updated files in the volume and reload data when they’re changed.
- Add ability to upload and save Ms word / google sheet debrief documents into the web page and view them.
- Add ability to create and store debrief notes in the website.
- Add ability to store rig information / to do list in the website.
- Can we link these files to a google drive folder?
- CHANGE THE PASSWORD.
- Later:
- Would be good to implement a SQL database or similar to store the data instead of storing it as part of the memory.
- Also need to write up notes on how to change files I the railway volume.
- compare actual sailing data against target polars,
- edit polar curves,
- update sail selection charts,
- add notes/events,
- save analysis sessions and export useful outputs

## Additional available Markdown release history

#### 0.9.5.4
- Restructured the 0.9.4 static web content into page fragments and page-specific JavaScript files.
- No intended functional changes.

### 0.9.4
- Added continuous colour scale bars to Map View, Variable plot and Polar plots.
- Made Plotly canvas backgrounds transparent against a darker plot shell.
- Fixed tack colours: port/negative TWA red; starboard/positive TWA green.
- Moved the sidebar control inline with the tabs and renamed GPS to Map View.
- Preferentially maps VMG_PCT from Expedition VMG%.
- Added filtered EventData/TestData viewer and TestData upload/volume loading.
