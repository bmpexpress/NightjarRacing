# Resilient loader patch changes

- Fixed sparse `Utc` values being stored as text and later rejecting every row.
- Added Excel serial timestamp parsing for both numeric values and numeric strings.
- Timestamp validation now happens per record; an invalid timestamp skips only that row.
- Added repeated/dynamic schema handling for sparse and standard Expedition logs.
- Header-name and channel-ID rows may have unequal widths and trailing blanks.
- Unknown sparse channel IDs skip only that value pair.
- Malformed/short records are counted and skipped without clearing accepted rows.
- A fatal CSV parser error retains rows accepted before the failure as a partial load.
- Reaching the 3,200 MiB loading guard retains accepted rows as a partial load.
- Log, polar, event, event-list and sail-chart loading are isolated from one another.
- Failed uploads preserve the previously loaded valid dataset.
- Expedition event files support preambles, repeated/reordered headers and short rows.
- Added load diagnostics and regression tests.
