# Nightjar Data Analysis 0.9.0 — efficient resilient build

This is a complete GitHub-ready Java/Spring Boot project. It supersedes the earlier patch archives.

## Important fixes

- Sequential 1 MiB-buffered logfile parsing; no whole-log byte array or decoded String.
- Compact sparse row storage instead of a `LinkedHashMap` per incoming row.
- Repeated/changing Expedition header blocks supported in sparse and ordinary CSV logs.
- Numeric Excel UTC values work as numbers **and** strings, including serial values between 0 and 1.
- Invalid timestamps, malformed rows, unknown channel IDs and wrong-boat records are skipped individually.
- Valid rows already accepted survive an unrecoverable later CSV record or the memory guard.
- Log, polar, event, event-list and sail-chart loading are isolated; one bad file does not clear the others.
- Failed uploaded replacements preserve the existing working dataset.
- Event files detect repeated/reordered headers and tolerate short metadata records.
- VMG/VMG% calculations stop safely at the guard without removing source rows.
- CSV response uses a streaming HTTP body.

## Figure downsampling controls

Settings contains:

- **Enable deterministic downsampling for figures** — default **off**.
- **Maximum points per figure** — default **10,000**, allowed range 100–2,000,000.

The setting applies only to `/api/plot-data`, used by Overview, Polar, GPS and Variable plots. The sample is evenly spaced across the matched sequence and preserves the first and last point.

It does **not** apply to:

- Stored logfile rows.
- Filtering calculations.
- Full `/api/data` results.
- CSV exports.

The UI reports matched and returned point counts and whether downsampling was applied. With the option off, every matched point is sent to each figure; this may be slow for very large selections.

## Memory limits for the 8 GB workspace

The Docker image defaults to:

```text
JAVA_TOOL_OPTIONS=-Xms256m -Xmx4096m -Xss512k -XX:+UseG1GC -XX:MaxDirectMemorySize=256m -XX:MaxMetaspaceSize=256m -XX:+ExitOnOutOfMemoryError
NIGHTJAR_LOAD_HEAP_LIMIT_MB=3200
```

The loader guard is deliberately below the 4 GiB heap ceiling to leave room for sorting, calculated channels and requests. The supplied limits leave substantial headroom beneath a 6 GB process target, although real RSS must still be checked in the deployment metrics.

## Build and test

```bash
mvn clean test package
java -jar target/nightjar-data-analysis-0.9.0.jar
```

Or:

```bash
docker build -t nightjar-090 .
docker run --rm -p 8080:8080 -v /local/Data:/Data nightjar-090
```

Open `http://localhost:8080`.

## Railway

Use Dockerfile deployment and this custom start command:

```bash
java -jar /app/app.jar
```

The project honours `PORT`. Optional variables:

```text
NIGHTJAR_DATA_DIR=/Data
NIGHTJAR_APP_PASSWORD_SHA256=<recommended SHA-256 digest>
NIGHTJAR_APP_PASSWORD=<plain fallback>
```

## Default data names

```text
/Data/logfile.csv
/Data/Polar.txt
/Data/EventData.csv
/Data/EventList.txt
/Data/SailChart.xml
```

## Expected logging

```text
Loading /Data/logfile.csv sequentially (... bytes)
Sequential log load: 250,000 valid rows; 2 invalid timestamps; heap 410 / 3,200 MiB
Loaded 730,000 valid rows sequentially; heap 1,450 MiB.
```

Warnings identify skipped rows and partial loads without changing a valid dataset to zero rows.
