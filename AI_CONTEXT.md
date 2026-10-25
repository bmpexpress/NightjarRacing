# Nightjar: Current Project Context

## Source baseline and release
- Project: Nightjar Data Analysis, a sailing/racing analytics website.
- Supplied implementation baseline: Python/Streamlit 0.10.0, confirmed by app.py and the latest supplied changelog entry.
- Delivered source version: 0.10.1. User acceptance and live deployment have not been verified.
- The supplied context file's 0.8.1.0 release field was stale. Java 0.9.x is historical, not the current architecture.
- Source control recorded in the supplied context: GitHub, managed locally with GitHub Desktop on Windows. Deployment platform recorded: Railway; branch recorded: Dev. Live repository/branch settings were not inspected.

## Files and runtime
- app.py: application entry point main(), data parsers, storage helpers, calculations, styling and page rendering.
- requirements.txt: Streamlit >=1.53,<2; pandas >=2.1,<3; NumPy >=1.26,<3; Plotly >=5.22,<7; tzdata >=2024.1; python-docx >=1.1,<2; DuckDB >=1.1,<2; PyArrow >=19,<20.
- .streamlit/config.toml: supplied as config.txt for attachment; theme unchanged by this release.
- CHANGELOG.md: 0.10.1 implementation/checks followed by the supplied historical record.
- Known_Issues.md was referenced by the older context but was not attached in this session and was not modified.
- The source uses datetime.UTC, requiring Python 3.11 or newer. The tested runtime was Python 3.12.15.
- Recorded Railway start command, unchanged by this release: `python -m streamlit run app.py --server.address=0.0.0.0 --server.port=8080 --server.headless=true --browser.gatherUsageStats=false`.

## Current storage architecture
- Default mounted directory: /Data. Optional NIGHTJAR_DATA_DIR overrides it.
- Original root reference names remain logfile.csv, Polar.txt, EventData.csv, EventList.txt, TestData.csv, SailChart.xml and Logo.png.
- Persistent canonical master: /Data/.nightjar_store/CURRENT selects a generation directory.
- Each generation contains nightjar.duckdb, pruned working.parquet, metadata.json, archival parquet/ chunks, original inputs/ logfiles and canonical EventList/EventData/TestData/Polar files when available.
- DuckDB stores a persistent working_log view over the pruned working Parquet. Archival Parquet is queried explicitly for full exports, not retained as a resident master DataFrame.
- Imports write bounded parser chunks, classify channels globally, build the new working Parquet/catalogue and then atomically publish CURRENT. Previous committed snapshots remain recovery copies.
- Query connections are short-lived. SQL applies sidebar event/date/GUN/time filters before fetching only active-page channels. Full-resolution selected results still materialise for existing pandas/Plotly calculations and rendering.
- VMG calculation remains in the parser. Missing VMG percentage is filled only for queried data using the active polar. Constant scalar metadata can supply calculation inputs without a stored working column.
- Empty/constant working channels are reported in Settings. Timestamp keys remain; missing gaps prevent constant classification. Archives retain removed values, and append can reactivate a channel.
- Default DuckDB buffer budget: 256MB; threads: 2. Optional environment settings: NIGHTJAR_DB_MEMORY_LIMIT and NIGHTJAR_DB_THREADS. Total application memory is not bounded by the DuckDB buffer setting.

## Session lifecycle
- No global dataset or connection caches remain.
- A session-scoped resource stores only temporary-file paths under /Data/.nightjar_sessions. Its release callback removes preview/export files on session release.
- Sidebar log uploads are session-only previews; they do not replace the persistent master. Add event is disabled while a sidebar log override is active.
- Sign-out clears the current session and its temporary-file resource. Persistent .nightjar_store data remains.
- Garbage collection and best-effort Linux allocator trimming run after script execution. Streamlit/native buffers and disconnect timing prevent an immediate zero-process-memory guarantee.

## Event management and exports
- Settings/Add event accepts a logfile, date, Inshore/Offshore classification and event name, with optional revised EventData, TestData and polar.
- EventData/TestData merge by exact row; modified rows with different values are retained alongside existing rows. A revised polar replaces the active polar in the new snapshot.
- Exact duplicate logfiles are rejected by SHA-256; overlapping records in different files are retained. No timestamp-only deduplication is performed.
- Original root files remain unchanged by web imports. The canonical merged files are inside the active generation. Existing external root reference-file edits are detected by signature; external master-log changes are reported as conflicts to protect appended imports.
- EventData/TestData and the map event table filter by selected event dates, or date range. UTC event times are converted to the chosen log clock for date matching without changing displayed source cells.
- Downloads: full master, sidebar-filtered master and current-tab processed native channels. Excel-date Utc values retain the source log clock. Native sparse format uses source channel IDs only; extracted CSV retains available native columns. Existing filtered CSV and session-settings downloads remain.
- Export preparation is explicit. Streamlit still holds a prepared download payload in memory while serving it.

## Preserved analytical conventions and scope
- VMG values and VMG percentages remain separate. VMC is not VMG.
- Positive signed TWA is Starboard/green; negative signed TWA is Port/red.
- GUN timestamps are treated as UTC; default naive log clock is Europe/London, with UTC selectable in Settings. Date-specific DST correction and the five-minute lead-in remain.
- Event association remains date-based and uses the first GUN per day. Separate same-day race windows were not added.
- Existing styling, authentication, navigation, full-resolution plots, averaging, tolerances, variable controls, debrief reading and sail-chart routines remain. Constant/empty channel removal is the intentional requested change to variable availability.

## Verification and remaining evidence
- Syntax, storage, round-trip, transaction-failure, GUN/date-filter, scalar-calculation and cleanup checks passed using constructed fixtures.
- Streamlit AppTest passed all eight pages, channel-selection changes, export preparation, appended-event selection, sign-out and empty selections.
- 55 existing functions/classes, CSS, aliases and default filenames were unchanged by AST comparison.
- No actual sailing log was attached. Expedition import, real browser disconnect, production RAM behaviour, Railway deployment and multi-replica operation remain unverified.
- Snapshots/archives increase disk use; automated retention is not implemented. Release notes contain manual tests and rollback details.
