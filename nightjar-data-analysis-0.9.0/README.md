# Nightjar Data Analysis 0.9.0 — resilient sequential-loader update

This folder is ready to copy into the existing Nightjar Java 0.9.0 GitHub repository. Preserve the paths when uploading.

## Replace/add these files

- Replace `src/main/java/com/nightjar/analysis/DataStore.java`
- Replace `src/main/java/com/nightjar/analysis/Models.java`
- Replace `src/main/resources/application.properties`
- Replace `Dockerfile`
- Replace `railway.toml`
- Add `src/test/java/com/nightjar/analysis/DataStoreResilientLoaderTest.java`
- Optionally retain `railway-variables.env.example` as documentation; do not commit real passwords.

No changes are required to `WebController.java`, `NightjarApplication.java`, `pom.xml`, or the static website files.

## Why the previous deployment reported zero rows

The deployment log showed more than 501,000 physical records being read, followed by `Loaded 0 rows sequentially`. Sparse Expedition UTC values were retained as Strings. Numeric Excel-style UTC strings therefore failed timestamp conversion and every record was removed after reading.

This update performs timestamp conversion while each record is read and recognises Excel serial dates supplied either as a Java Number or numeric text.

## Resilience changes

### Dynamic logfile schemas

Both sparse and standard log readers recognise repeated header sections. A new `!Boat,Utc,...` row resets the sparse schema, and the following `!Boat,<channel id>,...` row rebuilds the ID-to-name map. Header and ID row widths are paired with `Math.min(...)`, so a trailing blank or added/removed variable does not invalidate the section.

Standard CSV files similarly discover repeated headers containing a timestamp channel and update the current column positions.

### Row-level failures

- Invalid timestamp: skip that row only.
- Short/malformed row: skip that row only.
- Unknown sparse channel ID: skip that value pair only.
- Odd trailing sparse field: retain the recognised part of the row and count a warning.
- Other boat number: skip that row only.
- Repeated or changed schema: rebuild the mapping and continue.
- Fatal parser error after valid rows: keep the previously accepted rows as a partial load.
- Loader memory guard reached: keep accepted rows as a partial load rather than discarding them.

### Isolated file loading

The startup sequence loads the logfile, polar, Expedition events, event list, and sail chart in independent guarded operations. A bad supporting file cannot erase a successful logfile load. An uploaded replacement is assigned only after its parser returns a valid non-empty result, so a failed replacement preserves the previous working data.

The Expedition-events parser now:

- Discovers its header rather than assuming the first row is the header.
- Accepts repeated/reordered headers.
- Checks field indexes before access.
- Retains valid event rows while skipping short/malformed rows.
- Avoids `Index for header 'Type' ... CSVRecord only has 1 values`.

### Diagnostics

`/api/state` now includes:

- `loadStatus`
- `loadWarnings`
- `heapUsedMiB`
- `heapMaxMiB`
- `loadHeapLimitMiB`

The loader logs accepted rows, invalid timestamps, malformed rows, skipped boat rows, header-section count, memory state, and up to five rejected timestamp examples when no row is valid.

## Memory configuration for the 8 GB workspace

The included Dockerfile uses:

```text
JAVA_TOOL_OPTIONS=-Xms256m -Xmx4096m -Xss512k -XX:+UseG1GC -XX:MaxDirectMemorySize=256m -XX:MaxMetaspaceSize=256m -XX:+ExitOnOutOfMemoryError
NIGHTJAR_LOAD_HEAP_LIMIT_MB=3200
```

The loader reads the logfile through a 1 MiB buffer. The 3,200 MiB load guard leaves room inside the 4 GiB heap for sorting and calculations, while the 4 GiB heap and bounded native areas give substantial headroom beneath the desired 6 GB process ceiling.

If the guard is reached, useful rows are retained and clearly labelled as a partial load.

## Railway

Custom start command:

```bash
java -jar /app/app.jar
```

The JVM automatically reads `JAVA_TOOL_OPTIONS`.

## Validate before merging

From the repository root:

```bash
mvn clean test package
```

Or build the same Docker image used by Railway:

```bash
docker build -t nightjar-090 .
docker run --rm -p 8080:8080 -v /local/path/to/Data:/Data nightjar-090
```

Expected startup logging resembles:

```text
Loading /Data/logfile.csv sequentially (... bytes)
Sequential log load: 250,000 valid rows; 2 invalid timestamps; heap 410 / 3,200 MiB
Loaded 730,000 valid rows sequentially; heap 1,450 MiB. seen=..., accepted=..., schema sections=...
Expedition events loaded from /Data/EventData.csv
Tomcat started on port 8080
```

A small number of rejected rows should be reported as warnings without changing the valid row count to zero.

## Remaining consideration

The `/api/data` endpoint in the current 0.9.0 architecture constructs the complete filtered JSON response in memory. The loader is now bounded and resilient, but returning an unfiltered multi-million-row dataset can still create a separate server/browser memory peak. Event/date filtering remains advisable until that endpoint is converted to pagination or streaming.
