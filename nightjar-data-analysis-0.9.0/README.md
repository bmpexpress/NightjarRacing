# Nightjar 0.9.0 — sequential logfile loader patch

This patch replaces the memory-heavy logfile path in the Java 0.9.0 project.

## Replace these files

Copy the files in this archive over the same paths in the existing Java project:

- `src/main/java/com/nightjar/analysis/DataStore.java`
- `src/main/java/com/nightjar/analysis/Models.java`
- `src/main/resources/application.properties`
- `Dockerfile`
- `railway.toml`

Do not replace `WebController.java`, `NightjarApplication.java` or the static website files.

## What changed

1. `logfile.csv` is opened as a buffered `InputStream` and parsed record by record.
2. Uploads use `MultipartFile.getInputStream()` instead of `getBytes()`.
3. The loader no longer creates a whole-file byte array and a second whole-file Java String.
4. Per-row `LinkedHashMap` storage is replaced with compact parallel key/value arrays. Blank sparse channels allocate nothing.
5. New data are committed only after a complete successful parse; a failed replacement does not destroy a working dataset.
6. Heap is checked every 2,048 accepted rows, with progress reported approximately every 250,000 rows.
7. At the default 3,200 MiB loading threshold, loading stops cleanly before the 4 GiB heap is exhausted.
8. A guarded startup failure leaves the web server online rather than creating a Railway restart loop.
9. `/api/state` reports `heapUsedMiB`, `heapMaxMiB`, `loadHeapLimitMiB` and `loadStatus`.

## Railway variables

The Dockerfile defaults are:

```text
JAVA_TOOL_OPTIONS=-Xms256m -Xmx4096m -Xss512k -XX:+UseG1GC -XX:MaxDirectMemorySize=256m -XX:MaxMetaspaceSize=256m -XX:+ExitOnOutOfMemoryError
NIGHTJAR_LOAD_HEAP_LIMIT_MB=3200
```

These settings are intentionally conservative for an 8 GB workspace. A 4 GiB Java heap, a 3.125 GiB loader guard, plus bounded direct memory and metaspace normally leaves more than 1 GiB below the requested 6 GB process target for JVM native memory, code cache, threads and short-lived operating overhead.

Use this custom start command:

```bash
java -jar /app/app.jar
```

`JAVA_TOOL_OPTIONS` is read by Java automatically, so the custom command does not need `$JAVA_OPTS` expansion.

## Expected log messages

A successful load reports messages such as:

```text
Loading /Data/logfile.csv sequentially (... bytes)
Sequential log load: 250,000 rows; heap 420 / 3,200 MiB
Loaded 1,250,000 rows sequentially; heap 1,840 MiB
```

If the configured guard is reached, the application remains online and reports:

```text
Log loading stopped safely ... because heap reached ... MiB
```

## Important limitation

This patch makes parsing sequential and substantially reduces retained row overhead, but it still keeps the final parsed dataset in RAM because the current analysis APIs expect an in-memory dataset. If the compact final dataset itself exceeds the guarded heap threshold, it cannot be loaded in full under this design. The next architectural step would be a disk-backed columnar or embedded-database store.

Also note that `/api/data` currently materialises the complete filtered response as maps before JSON serialisation. A very broad filter can therefore create a separate memory spike after loading. Keep an event/date filter active for very large logs, or change that endpoint to stream JSON in a later patch.

## Build and test

```bash
mvn clean test package
docker build -t nightjar-090 .
docker run --rm -p 8080:8080 -v /your/data:/Data nightjar-090
```

Monitor the process while loading:

```bash
docker stats
```

The Java heap ceiling is 4 GiB. Total container memory is expected to remain below 6 GB with the supplied native-memory bounds, but RSS should still be verified with the real logfile because JVM/native behaviour and concurrent requests vary by deployment environment.
