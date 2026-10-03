# Changelog

## 0.9.5
- Split the monolithic front end into ES modules by responsibility and tab.
- Split visual page content into reusable HTML fragments under `static/pages`.
- Reduced `index.html` to a lightweight application shell.
- Added a dedicated API module, state store and common rendering utilities.
- Kept individual modules for Overview, Polar, Sail selection, Map View, Variable plot, Files and Settings.
- Added explicit Map View centre and zoom calculation from the displayed data extents.
- Kept EventData and TestData loading through `/api/file-data/{source}` with visible row counts and table status.
- Updated project, display and export versions to 0.9.5.
