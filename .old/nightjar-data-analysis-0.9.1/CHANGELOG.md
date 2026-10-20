## 0.9.1 memory-efficiency revision
- Figure downsampling is enabled by default to constrain browser and server response memory.
- Plot filtering now counts and samples without retaining a second list of every matched row.
- Browser responses release the duplicate `rows` reference after refresh.
- Only the active Plotly view is rendered; inactive plot objects are purged when tabs change.
- Versioned downloads and application metadata updated to 0.9.1.

# 0.9.0 efficient-loader revision

- Corrected the failed Excel timestamp regression: serials from 0 upwards are valid.
- Sequential, memory-guarded standard and sparse Expedition loading.
- Repeated and changing header sections supported.
- Per-row/per-value error isolation and partial-load retention.
- Independent logfile, polar, event-list, event and sail-chart loading.
- Optional deterministic figure downsampling, default off.
- User-adjustable maximum figure-point setting, default 10,000.
- Separate `/api/plot-data` and full `/api/data` behaviour.
- Streaming CSV HTTP response.
- Loader, BST, timestamp and downsampling regression tests.
