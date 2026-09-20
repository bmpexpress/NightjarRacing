package com.nightjar.analysis;

import jakarta.annotation.PostConstruct;
import org.apache.commons.csv.*;
import org.apache.poi.xwpf.usermodel.XWPFDocument;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import org.w3c.dom.*;

import javax.xml.parsers.DocumentBuilderFactory;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.time.*;
import java.time.format.*;
import java.time.temporal.ChronoUnit;
import java.util.*;
import java.util.concurrent.locks.ReentrantReadWriteLock;
import java.util.stream.Collectors;

@Service
public class DataStore {
    private static final long MIB = 1024L * 1024L;
    private static final long DEFAULT_LOAD_HEAP_LIMIT_MB = 3200L;
    private static final long HEAP_RESERVE_MB = 512L;
    private static final int INPUT_BUFFER_BYTES = 1024 * 1024;
    private static final int PROGRESS_ROWS = 250_000;
    private static final int MAX_DIAGNOSTIC_SAMPLES = 5;

    private final ReentrantReadWriteLock lock = new ReentrantReadWriteLock();
    private List<Models.Row> rows = new ArrayList<>();
    private List<Models.EventDefinition> eventList = new ArrayList<>();
    private List<Models.ExpeditionEvent> expeditionEvents = new ArrayList<>();
    private List<Models.PolarPoint> polar = new ArrayList<>();
    private List<Models.SailPoint> sails = new ArrayList<>();
    private String debrief = "";
    private LinkedHashSet<String> columns = new LinkedHashSet<>();
    private LinkedHashSet<String> included = new LinkedHashSet<>();
    private LinkedHashMap<String,String> mapping = new LinkedHashMap<>();
    private volatile String loadStatus = "No log loaded";
    private final List<String> loadWarnings = new ArrayList<>();

    private static final ZoneId DATA_ZONE = ZoneId.of("Europe/London");
    private static final ZoneId GUN_ZONE = ZoneOffset.UTC;
    private static final Map<String,List<String>> ALIASES = Map.ofEntries(
        Map.entry("timestamp", List.of("utc","time","timestamp","datetime")),
        Map.entry("bsp", List.of("bsp","boat speed","log bsp")),
        Map.entry("twa", List.of("twa","true wind angle")),
        Map.entry("tws", List.of("tws","true wind speed")),
        Map.entry("awa", List.of("awa","apparent wind angle")),
        Map.entry("aws", List.of("aws")),
        Map.entry("vmg", List.of("vmg","velocity made good","vmg kt","vmg knots","vmg value","vmg kts")),
        Map.entry("vmg_pct", List.of("vmg%","vmg %","vmg pct","vmg percent","vmg_pct")),
        Map.entry("heel", List.of("heel")),
        Map.entry("drift", List.of("drift","tide rate")),
        Map.entry("lat", List.of("lat","latitude","lat1")),
        Map.entry("lon", List.of("lon","longitude","lon1")),
        Map.entry("sog", List.of("sog")), Map.entry("cog", List.of("cog")),
        Map.entry("sail", List.of("sail","foresail_id","foresail"))
    );

    private static final class ParseStats {
        long recordsSeen;
        long rowsAccepted;
        long invalidBoatRows;
        long invalidTimestampRows;
        long malformedRows;
        int schemaSections;
        boolean truncatedForMemory;
        boolean parserStoppedEarly;
        final List<String> rejectedTimestampSamples = new ArrayList<>();

        String summary() {
            return String.format(Locale.ROOT,
                "seen=%,d, accepted=%,d, invalid timestamps=%,d, malformed=%,d, " +
                "other boats=%,d, schema sections=%,d%s%s",
                recordsSeen, rowsAccepted, invalidTimestampRows, malformedRows,
                invalidBoatRows, schemaSections,
                truncatedForMemory ? ", memory-limited partial load" : "",
                parserStoppedEarly ? ", parser stopped after an unrecoverable record" : "");
        }
    }

    private record ParsedLog(List<Models.Row> rows,
                             LinkedHashSet<String> columns,
                             ParseStats stats) {}

    @PostConstruct
    void loadDefaultData() {
        Path dir = Path.of(System.getenv().getOrDefault("NIGHTJAR_DATA_DIR", "/Data"));
        lock.writeLock().lock();
        try {
            loadWarnings.clear();
            Path log = dir.resolve("logfile.csv");
            if (Files.exists(log)) {
                try {
                    System.out.printf(Locale.ROOT, "Loading %s sequentially (%,d bytes)%n", log, Files.size(log));
                    try (InputStream input = Files.newInputStream(log)) {
                        parseLog(input);
                    }
                } catch (Exception ex) {
                    warn("Logfile", ex);
                    // Do not clear a previously usable dataset. On a fresh start this
                    // leaves an empty site, but the application remains available.
                }
            }

            // Each supporting file is isolated. A bad event/polar/chart file cannot
            // discard a successfully loaded logfile or another supporting dataset.
            loadAuxiliary("Polar", dir.resolve("Polar.txt"),
                () -> polar = parsePolar(readSmallFile(dir.resolve("Polar.txt"))));
            loadAuxiliary("Expedition events", dir.resolve("EventData.csv"),
                () -> expeditionEvents = parseEvents(readSmallFile(dir.resolve("EventData.csv"))));
            loadAuxiliary("Event list", dir.resolve("EventList.txt"),
                () -> eventList = parseEventList(readSmallFile(dir.resolve("EventList.txt"))));
            loadAuxiliary("Sail chart", dir.resolve("SailChart.xml"),
                () -> sails = parseSails(readSmallFile(dir.resolve("SailChart.xml"))));

            try {
                addCalculatedVmgPct();
            } catch (Exception ex) {
                warn("VMG percentage calculation", ex);
            }
        } finally {
            lock.writeLock().unlock();
        }
    }

    private void loadAuxiliary(String label, Path path, ThrowingAction action) {
        if (!Files.exists(path)) return;
        try {
            action.run();
            System.out.println(label + " loaded from " + path);
        } catch (Exception ex) {
            warn(label, ex);
        }
    }

    @FunctionalInterface
    private interface ThrowingAction { void run() throws Exception; }

    private void warn(String component, Exception ex) {
        String message = component + " was skipped: " + Objects.toString(ex.getMessage(), ex.getClass().getSimpleName());
        loadWarnings.add(message);
        System.err.println(message);
    }

    private static byte[] readSmallFile(Path path) {
        try { return Files.readAllBytes(path); }
        catch (IOException ex) { throw new UncheckedIOException(ex); }
    }

    public Map<String,Object> state() {
        lock.readLock().lock();
        try {
            LinkedHashMap<String,Object> state = new LinkedHashMap<>();
            state.put("version", NightjarApplication.VERSION);
            state.put("loaded", !rows.isEmpty());
            state.put("rowCount", rows.size());
            state.put("columns", columns);
            state.put("includedVariables", included);
            state.put("mapping", mapping);
            state.put("eventList", eventList);
            state.put("polar", polar);
            state.put("sails", sails);
            state.put("gunEvents", expeditionEvents.stream()
                .filter(e -> e.utcTime() != null && isGun(e))
                .map(e -> Map.of(
                    "utc", e.utcTime(),
                    "local", gunLocal(e.utcTime()),
                    "type", Objects.toString(e.type(), ""),
                    "comment", Objects.toString(e.comment(), "")))
                .toList());
            state.put("debrief", debrief);
            state.put("loadStatus", loadStatus);
            state.put("loadWarnings", List.copyOf(loadWarnings));
            state.put("dataTimeZone", DATA_ZONE.getId());
            state.put("gunTimeZone", GUN_ZONE.getId());
            state.put("heapUsedMiB", usedHeapBytes() / MIB);
            state.put("heapMaxMiB", Runtime.getRuntime().maxMemory() / MIB);
            state.put("loadHeapLimitMiB", loadHeapLimitBytes() / MIB);
            return state;
        } finally { lock.readLock().unlock(); }
    }

    public void upload(MultipartFile log, MultipartFile polarFile, MultipartFile events,
                       MultipartFile eventListFile, MultipartFile sailChart,
                       MultipartFile debriefFile) throws Exception {
        lock.writeLock().lock();
        try {
            loadWarnings.clear();
            if (log != null && !log.isEmpty()) {
                try (InputStream input = log.getInputStream()) {
                    parseLog(input); // commits only accepted rows after parsing
                } catch (Exception ex) {
                    warn("Uploaded logfile", ex); // old good log remains in place
                }
            }
            if (polarFile != null && !polarFile.isEmpty()) {
                replaceSafely("Uploaded polar", () -> polar = parsePolar(polarFile.getBytes()));
            }
            if (events != null && !events.isEmpty()) {
                replaceSafely("Uploaded Expedition events", () -> expeditionEvents = parseEvents(events.getBytes()));
            }
            if (eventListFile != null && !eventListFile.isEmpty()) {
                replaceSafely("Uploaded event list", () -> eventList = parseEventList(eventListFile.getBytes()));
            }
            if (sailChart != null && !sailChart.isEmpty()) {
                replaceSafely("Uploaded sail chart", () -> sails = parseSails(sailChart.getBytes()));
            }
            if (debriefFile != null && !debriefFile.isEmpty()) {
                replaceSafely("Uploaded debrief", () -> debrief = parseDebrief(debriefFile));
            }
            try { addCalculatedVmgPct(); }
            catch (Exception ex) { warn("VMG percentage calculation", ex); }
        } finally { lock.writeLock().unlock(); }
    }

    private void replaceSafely(String label, ThrowingAction replacement) {
        try { replacement.run(); }
        catch (Exception ex) { warn(label, ex); }
    }

    public void updateSettings(Models.SettingsRequest request) {
        lock.writeLock().lock();
        try {
            included = request.includedVariables() == null
                ? new LinkedHashSet<>(columns)
                : request.includedVariables().stream().filter(columns::contains)
                    .collect(Collectors.toCollection(LinkedHashSet::new));
            if (request.mapping() != null) {
                request.mapping().forEach((key,value) -> {
                    if (value == null || value.isBlank() || columns.contains(value)) {
                        mapping.put(key, blankToNull(value));
                    }
                });
            }
        } finally { lock.writeLock().unlock(); }
    }

    public Models.DataResponse filtered(Models.FilterRequest request) {
        lock.readLock().lock();
        try {
            Set<String> visible = request.includedVariables() == null
                ? new LinkedHashSet<>(included)
                : request.includedVariables().stream().filter(included::contains)
                    .collect(Collectors.toCollection(LinkedHashSet::new));
            String tsCol = mapping.get("timestamp");
            Set<String> selectedEvents = request.events() == null ? Set.of() : new HashSet<>(request.events());
            Set<LocalDate> selectedDates = eventList.stream()
                .filter(e -> selectedEvents.contains(e.event()))
                .map(Models.EventDefinition::date).collect(Collectors.toSet());
            LocalDate from = parseDate(request.fromDate()), to = parseDate(request.toDate());
            LocalTime start = parseTime(request.startTime(), LocalTime.MIN);
            LocalTime end = parseTime(request.endTime(), LocalTime.MAX.truncatedTo(ChronoUnit.SECONDS));
            List<String> warnings = new ArrayList<>(loadWarnings);
            Map<LocalDate,LocalDateTime> gunCutoffs = gunCutoffs(selectedDates, warnings);
            ArrayList<Map<String,Object>> result = new ArrayList<>();
            for (Models.Row row : rows) {
                LocalDateTime stamp = row.timestamp;
                if (stamp == null) continue;
                LocalDate day = stamp.toLocalDate();
                if (!selectedDates.isEmpty() && !selectedDates.contains(day)) continue;
                if (selectedDates.isEmpty() && ((from != null && day.isBefore(from)) || (to != null && day.isAfter(to)))) continue;
                LocalDateTime cutoff = gunCutoffs.get(day);
                if (cutoff != null && stamp.isBefore(cutoff)) continue;
                if (request.trimByTime() && (stamp.toLocalTime().isBefore(start) || stamp.toLocalTime().isAfter(end))) continue;
                result.add(row.toMap(visible, tsCol));
            }
            return new Models.DataResponse(result, warnings, rows.size(), result.size(), new LinkedHashMap<>(mapping));
        } finally { lock.readLock().unlock(); }
    }

    private Map<LocalDate,LocalDateTime> gunCutoffs(Set<LocalDate> selectedDates, List<String> warnings) {
        HashMap<LocalDate,LocalDateTime> output = new HashMap<>();
        for (LocalDate date : selectedDates) {
            Optional<Models.ExpeditionEvent> gun = expeditionEvents.stream()
                .filter(e -> e.utcTime() != null && isGun(e) && gunLocal(e.utcTime()).toLocalDate().equals(date))
                .min(Comparator.comparing(Models.ExpeditionEvent::utcTime));
            if (gun.isEmpty()) warnings.add("No GUN entry found for " + date + ". Filter manually if required.");
            else output.put(date, gunLocal(gun.get().utcTime()).minusMinutes(5));
        }
        return output;
    }

    private static boolean isGun(Models.ExpeditionEvent event) {
        return (Objects.toString(event.type(), "") + " " + Objects.toString(event.comment(), ""))
            .toLowerCase(Locale.ROOT).contains("gun");
    }

    static LocalDateTime gunLocal(LocalDateTime utc) {
        return utc.atZone(GUN_ZONE).withZoneSameInstant(DATA_ZONE).toLocalDateTime();
    }


    /**
     * Sequential logfile entry point. The source is never copied to a whole-file
     * byte array or String. Invalid records are omitted individually. If a fatal
     * parser or memory-bound condition occurs after useful rows have been read,
     * those accepted rows are retained as a clearly reported partial load.
     */
    void parseLog(InputStream source) throws IOException {
        BufferedInputStream buffered = source instanceof BufferedInputStream b
            ? b : new BufferedInputStream(source, INPUT_BUFFER_BYTES);
        boolean sparse = startsWithSparseMarker(buffered);
        ParsedLog parsed = sparse
            ? parseSparseLog(utf8Reader(buffered))
            : parseStandardLog(utf8Reader(buffered));

        if (parsed.rows().isEmpty()) {
            throw new IllegalArgumentException(
                "No valid log rows remained. " + parsed.stats().summary() +
                (parsed.stats().rejectedTimestampSamples.isEmpty() ? "" :
                    ". Rejected timestamp examples: " + parsed.stats().rejectedTimestampSamples));
        }

        LinkedHashMap<String,String> newMapping = detectMappings(parsed.columns());
        if (newMapping.get("timestamp") == null) {
            throw new IllegalArgumentException("No timestamp/UTC channel was discovered. " + parsed.stats().summary());
        }

        if (!timestampsAreOrdered(parsed.rows())) {
            parsed.rows().sort(Comparator.comparing(row -> row.timestamp));
        }

        // Atomic logical commit: no existing good dataset is replaced until a
        // usable new collection has been produced.
        rows = parsed.rows();
        columns = parsed.columns();
        mapping = newMapping;
        included = new LinkedHashSet<>(columns);
        addCalculatedVmg();

        String partial = parsed.stats().truncatedForMemory || parsed.stats().parserStoppedEarly
            ? " PARTIAL LOAD; see warnings." : "";
        loadStatus = String.format(Locale.ROOT,
            "Loaded %,d valid rows sequentially; heap %,d MiB.%s %s",
            rows.size(), usedHeapBytes()/MIB, partial, parsed.stats().summary());
        if (parsed.stats().truncatedForMemory) {
            loadWarnings.add("The logfile was retained as a partial load because the configured heap guard was reached.");
        }
        if (parsed.stats().parserStoppedEarly) {
            loadWarnings.add("The logfile was retained up to the point where the CSV parser could not recover.");
        }
        if (parsed.stats().invalidTimestampRows > 0 || parsed.stats().malformedRows > 0) {
            loadWarnings.add(String.format(Locale.ROOT,
                "Skipped %,d rows with invalid timestamps and %,d malformed rows.",
                parsed.stats().invalidTimestampRows, parsed.stats().malformedRows));
        }
        System.out.println(loadStatus);
    }

    private ParsedLog parseSparseLog(Reader reader) throws IOException {
        ArrayList<Models.Row> accepted = new ArrayList<>();
        LinkedHashSet<String> discovered = new LinkedHashSet<>(List.of("Boat", "Utc"));
        ParseStats stats = new ParseStats();
        List<String> names = null;
        Map<String,String> channelById = new HashMap<>();

        try (CSVParser parser = CSVFormat.DEFAULT.builder()
                .setIgnoreEmptyLines(true).setTrim(true).get().parse(reader)) {
            Iterator<CSVRecord> iterator = parser.iterator();
            while (true) {
                CSVRecord record;
                try {
                    if (!iterator.hasNext()) break;
                    record = iterator.next();
                } catch (RuntimeException parserFailure) {
                    stats.parserStoppedEarly = true;
                    stats.malformedRows++;
                    System.err.println("Sparse CSV parser stopped after record " + stats.recordsSeen +
                        "; earlier valid rows will be retained: " + parserFailure.getMessage());
                    break;
                }

                stats.recordsSeen++;
                try {
                    if (record.size() == 0) continue;
                    String first = clean(record.get(0));
                    String second = record.size() > 1 ? clean(record.get(1)) : "";

                    // Every !Boat,Utc,... line begins a new schema section. This is
                    // expected in Expedition logs when the recorded variable set changes.
                    if ("!boat".equalsIgnoreCase(first) && "utc".equalsIgnoreCase(second)) {
                        names = new ArrayList<>(record.size());
                        for (String value : record) names.add(stripHeaderMarker(clean(value)));
                        channelById.clear();
                        stats.schemaSections++;
                        continue;
                    }

                    // The following !Boat,<numeric-id>,... line maps channel IDs to
                    // the current names. Widths need not match; trailing blanks are safe.
                    if ("!boat".equalsIgnoreCase(first) && isInteger(second)) {
                        channelById.clear();
                        if (names == null) {
                            stats.malformedRows++;
                            continue;
                        }
                        int width = Math.min(names.size(), record.size());
                        for (int i = 0; i < width; i++) {
                            String id = clean(record.get(i));
                            String channel = names.get(i);
                            if (isInteger(id) && !channel.isBlank()) {
                                channelById.put(id, channel);
                                discovered.add(channel);
                            }
                        }
                        continue;
                    }

                    if (first.startsWith("!")) continue; // Other metadata/header records.
                    if (record.size() < 2) { stats.malformedRows++; continue; }
                    if (!"0".equals(first)) { stats.invalidBoatRows++; continue; }

                    Object rawUtc = typed(second); // Critical: numeric text becomes Double.
                    LocalDateTime timestamp = parseDateTime(rawUtc);
                    if (timestamp == null) {
                        rejectTimestamp(stats, second);
                        continue;
                    }

                    Models.Row row = new Models.Row(Math.max(8, record.size()/2 + 4));
                    row.timestamp = timestamp;
                    row.values.put("Boat", typed(first));
                    row.values.put("Utc", rawUtc);

                    // Sparse records are channel-id/value pairs. An odd trailing field,
                    // unknown ID or blank value invalidates only that pair, not the row.
                    for (int position = 2; position + 1 < record.size(); position += 2) {
                        String channel = channelById.get(clean(record.get(position)));
                        if (channel == null || channel.isBlank()) continue;
                        Object value = typed(record.get(position + 1));
                        if (value != null) row.values.put(channel, value);
                    }
                    if ((record.size() - 2) % 2 != 0) stats.malformedRows++;

                    accepted.add(row);
                    stats.rowsAccepted++;
                    if (!withinLoadBudget(stats)) break;
                } catch (RuntimeException badRow) {
                    stats.malformedRows++;
                    if (stats.malformedRows <= MAX_DIAGNOSTIC_SAMPLES) {
                        System.err.println("Skipping malformed sparse record " + stats.recordsSeen +
                            ": " + badRow.getMessage());
                    }
                }
            }
        }
        return new ParsedLog(accepted, discovered, stats);
    }

    private ParsedLog parseStandardLog(Reader reader) throws IOException {
        ArrayList<Models.Row> accepted = new ArrayList<>();
        LinkedHashSet<String> discovered = new LinkedHashSet<>();
        ParseStats stats = new ParseStats();
        List<String> headers = null;
        int timestampIndex = -1;
        int boatIndex = -1;

        // Do not bind Commons CSV to the first physical row. Expedition exports can
        // contain preamble rows and can repeat/change the header later in the file.
        try (CSVParser parser = CSVFormat.DEFAULT.builder().setIgnoreEmptyLines(true)
                .setTrim(true).get().parse(reader)) {
            Iterator<CSVRecord> iterator = parser.iterator();
            while (true) {
                CSVRecord record;
                try {
                    if (!iterator.hasNext()) break;
                    record = iterator.next();
                } catch (RuntimeException parserFailure) {
                    stats.parserStoppedEarly = true;
                    stats.malformedRows++;
                    System.err.println("Standard CSV parser stopped after record " + stats.recordsSeen +
                        "; earlier valid rows will be retained: " + parserFailure.getMessage());
                    break;
                }
                stats.recordsSeen++;
                try {
                    if (record.size() == 0) continue;
                    List<String> possibleHeader = standardHeader(record);
                    if (!possibleHeader.isEmpty()) {
                        headers = possibleHeader;
                        discovered.addAll(headers);
                        LinkedHashMap<String,String> currentMapping = detectMappings(new LinkedHashSet<>(headers));
                        timestampIndex = headers.indexOf(currentMapping.get("timestamp"));
                        boatIndex = indexOfIgnoreCase(headers, "Boat");
                        stats.schemaSections++;
                        continue;
                    }
                    if (headers == null) continue; // preamble/metadata before first real header
                    if (boatIndex >= 0 && boatIndex < record.size() &&
                            !"0".equals(clean(record.get(boatIndex)))) {
                        stats.invalidBoatRows++;
                        continue;
                    }
                    if (timestampIndex < 0 || timestampIndex >= record.size()) {
                        rejectTimestamp(stats, "<missing timestamp field>");
                        continue;
                    }
                    Object rawTimestamp = typed(record.get(timestampIndex));
                    LocalDateTime timestamp = parseDateTime(rawTimestamp);
                    if (timestamp == null) {
                        rejectTimestamp(stats, record.get(timestampIndex));
                        continue;
                    }
                    Models.Row row = new Models.Row(Math.max(8, headers.size() + 2));
                    row.timestamp = timestamp;
                    int width = Math.min(headers.size(), record.size());
                    for (int i = 0; i < width; i++) {
                        Object value = typed(record.get(i));
                        if (value != null) row.values.put(headers.get(i), value);
                    }
                    accepted.add(row);
                    stats.rowsAccepted++;
                    if (!withinLoadBudget(stats)) break;
                } catch (RuntimeException badRow) {
                    stats.malformedRows++;
                    if (stats.malformedRows <= MAX_DIAGNOSTIC_SAMPLES) {
                        System.err.println("Skipping malformed standard record " + stats.recordsSeen +
                            ": " + badRow.getMessage());
                    }
                }
            }
        }
        return new ParsedLog(accepted, discovered, stats);
    }

    private static List<String> standardHeader(CSVRecord record) {
        ArrayList<String> candidate = new ArrayList<>(record.size());
        boolean hasTimestamp = false;
        for (String field : record) {
            String name = stripHeaderMarker(clean(field));
            candidate.add(name);
            String normal = normalise(name);
            if (normal.equals("utc") || normal.equals("time") ||
                    normal.equals("timestamp") || normal.equals("datetime")) {
                hasTimestamp = true;
            }
        }
        return hasTimestamp && candidate.size() >= 2 ? candidate : List.of();
    }

    private static void rejectTimestamp(ParseStats stats, Object value) {
        stats.invalidTimestampRows++;
        if (stats.rejectedTimestampSamples.size() < MAX_DIAGNOSTIC_SAMPLES) {
            stats.rejectedTimestampSamples.add(Objects.toString(value, "<null>"));
        }
    }

    private static boolean withinLoadBudget(ParseStats stats) {
        long rows = stats.rowsAccepted;
        if (rows > 0 && rows % PROGRESS_ROWS == 0) {
            System.out.printf(Locale.ROOT,
                "Sequential log load: %,d valid rows; %,d invalid timestamps; heap %,d / %,d MiB%n",
                rows, stats.invalidTimestampRows, usedHeapBytes()/MIB, loadHeapLimitBytes()/MIB);
        }
        if ((rows & 2047L) != 0) return true;
        if (usedHeapBytes() < loadHeapLimitBytes()) return true;
        stats.truncatedForMemory = true;
        System.err.printf(Locale.ROOT,
            "Memory guard reached after %,d valid rows. Those rows will be retained; remaining input is skipped.%n",
            rows);
        return false;
    }

    private static boolean startsWithSparseMarker(BufferedInputStream source) throws IOException {
        source.mark(4096);
        byte[] prefix = source.readNBytes(4096);
        source.reset();
        String preview = new String(prefix, StandardCharsets.UTF_8).replace("\uFEFF", "").stripLeading();
        return preview.startsWith("!");
    }

    private static Reader utf8Reader(InputStream input) throws IOException {
        PushbackInputStream pushback = new PushbackInputStream(input, 3);
        byte[] prefix = pushback.readNBytes(3);
        if (!(prefix.length == 3 && (prefix[0]&0xff)==0xEF &&
                (prefix[1]&0xff)==0xBB && (prefix[2]&0xff)==0xBF)) {
            pushback.unread(prefix);
        }
        return new BufferedReader(new InputStreamReader(pushback, StandardCharsets.UTF_8), INPUT_BUFFER_BYTES);
    }

    private static boolean timestampsAreOrdered(List<Models.Row> data) {
        for (int i = 1; i < data.size(); i++) {
            if (data.get(i).timestamp.isBefore(data.get(i-1).timestamp)) return false;
        }
        return true;
    }

    private static long loadHeapLimitBytes() {
        long configured;
        try {
            configured = Long.parseLong(System.getenv().getOrDefault(
                "NIGHTJAR_LOAD_HEAP_LIMIT_MB", Long.toString(DEFAULT_LOAD_HEAP_LIMIT_MB)));
        } catch (NumberFormatException ex) {
            configured = DEFAULT_LOAD_HEAP_LIMIT_MB;
        }
        long maxHeap = Runtime.getRuntime().maxMemory();
        long safeForHeap = Math.max(512L*MIB, maxHeap - HEAP_RESERVE_MB*MIB);
        return Math.min(configured*MIB, safeForHeap);
    }

    private static long usedHeapBytes() {
        Runtime runtime = Runtime.getRuntime();
        return runtime.totalMemory() - runtime.freeMemory();
    }

    private static boolean isInteger(String value) {
        return value != null && value.matches("[+-]?\\d+");
    }

    private static String stripHeaderMarker(String value) {
        return value == null ? "" : value.replaceFirst("^!", "").trim();
    }

    private static String clean(String value) {
        return value == null ? "" : value.trim();
    }

    private static int indexOfIgnoreCase(List<String> values, String target) {
        for (int i = 0; i < values.size(); i++) {
            if (values.get(i).equalsIgnoreCase(target)) return i;
        }
        return -1;
    }


    private void addCalculatedVmg() {
        String existing = mapping.get("vmg"), bsp = mapping.get("bsp"), twa = mapping.get("twa");
        if (existing != null || bsp == null || twa == null) return;
        int calculated = 0;
        for (Models.Row row : rows) {
            Double speed = number(row.values.get(bsp));
            Double angle = number(row.values.get(twa));
            if (speed != null && angle != null) {
                row.values.put("VMG", speed * Math.cos(Math.toRadians(signedAngle(angle))));
                calculated++;
            }
            if ((calculated & 2047) == 0 && usedHeapBytes() >= loadHeapLimitBytes()) {
                loadWarnings.add("VMG calculation stopped at the heap guard; loaded source rows remain available.");
                break;
            }
        }
        if (calculated > 0) {
            columns.add("VMG");
            mapping.put("vmg", "VMG");
            included.add("VMG");
        }
    }

    private void addCalculatedVmgPct() {
        if (rows.isEmpty() || polar.isEmpty()) return;
        String existing = mapping.get("vmg_pct"), vmg = mapping.get("vmg");
        String tws = mapping.get("tws"), twa = mapping.get("twa");
        if (existing != null || vmg == null || tws == null || twa == null) return;

        Map<Double,List<Models.PolarPoint>> curves = polar.stream()
            .collect(Collectors.groupingBy(Models.PolarPoint::tws));
        double[] winds = curves.keySet().stream().mapToDouble(Double::doubleValue).sorted().toArray();
        int calculated = 0;
        for (Models.Row row : rows) {
            Double actual = number(row.values.get(vmg));
            Double wind = number(row.values.get(tws));
            Double angle = number(row.values.get(twa));
            Double target = wind == null || angle == null ? null
                : targetBsp(curves, winds, wind, Math.abs(signedAngle(angle)));
            double denominator = target == null ? Double.NaN
                : Math.abs(target * Math.cos(Math.toRadians(Math.abs(signedAngle(angle)))));
            if (actual != null && Double.isFinite(denominator) && denominator >= .05) {
                row.values.put("VMG_PCT", Math.abs(actual) / denominator * 100.0);
                calculated++;
            }
            if ((calculated & 2047) == 0 && calculated > 0 && usedHeapBytes() >= loadHeapLimitBytes()) {
                loadWarnings.add("VMG percentage calculation stopped at the heap guard; loaded source rows remain available.");
                break;
            }
        }
        if (calculated > 0) {
            columns.add("VMG_PCT");
            mapping.put("vmg_pct", "VMG_PCT");
            included.add("VMG_PCT");
        }
    }

    private static Double targetBsp(Map<Double,List<Models.PolarPoint>> curves,
                                    double[] winds, double tws, double twa) {
        if (winds.length == 0 || tws < winds[0] || tws > winds[winds.length-1]) return null;
        int upper = Arrays.binarySearch(winds, tws);
        if (upper < 0) upper = -upper - 1;
        int lower = upper == 0 ? 0 : upper - 1;
        if (upper >= winds.length) upper = winds.length - 1;
        Double low = angleInterpolate(curves.get(winds[lower]), twa);
        Double high = angleInterpolate(curves.get(winds[upper]), twa);
        if (low == null || high == null) return null;
        if (lower == upper) return low;
        double weight = (tws - winds[lower]) / (winds[upper] - winds[lower]);
        return low + weight * (high - low);
    }

    private static Double angleInterpolate(List<Models.PolarPoint> points, double twa) {
        List<Models.PolarPoint> sorted = points.stream()
            .sorted(Comparator.comparingDouble(Models.PolarPoint::twa)).toList();
        if (sorted.isEmpty() || twa < sorted.get(0).twa() || twa > sorted.get(sorted.size()-1).twa()) return null;
        for (int i = 0; i < sorted.size(); i++) {
            Models.PolarPoint current = sorted.get(i);
            if (Math.abs(current.twa() - twa) < 1e-9) return current.targetBsp();
            if (current.twa() > twa) {
                Models.PolarPoint previous = sorted.get(i-1);
                double weight = (twa - previous.twa()) / (current.twa() - previous.twa());
                return previous.targetBsp() + weight * (current.targetBsp() - previous.targetBsp());
            }
        }
        return sorted.get(sorted.size()-1).targetBsp();
    }

    private static double signedAngle(double angle) {
        return ((angle + 180.0) % 360.0 + 360.0) % 360.0 - 180.0;
    }

    private static LinkedHashMap<String,String> detectMappings(Set<String> names) {
        LinkedHashMap<String,String> output = new LinkedHashMap<>();
        Map<String,String> normalised = names.stream().collect(Collectors.toMap(
            DataStore::normalise, value -> value, (first, ignored) -> first, LinkedHashMap::new));
        ALIASES.forEach((key, aliases) -> {
            String found = aliases.stream().map(DataStore::normalise).map(normalised::get)
                .filter(Objects::nonNull).findFirst().orElse(null);
            if (found == null) {
                found = names.stream().filter(name -> aliases.stream()
                    .anyMatch(alias -> normalise(name).startsWith(normalise(alias))))
                    .findFirst().orElse(null);
            }
            output.put(key, found);
        });
        if (output.get("vmg") != null &&
                (output.get("vmg").contains("%") || normalise(output.get("vmg")).contains("pct"))) {
            output.put("vmg", null);
        }
        return output;
    }

    private static List<Models.PolarPoint> parsePolar(byte[] raw) {
        ArrayList<Models.PolarPoint> output = new ArrayList<>();
        for (String line : decode(raw).split("\\R")) {
            line = line.trim();
            if (line.isEmpty() || line.startsWith("!") || line.startsWith("#")) continue;
            try {
                double[] values = Arrays.stream(line.split("[\\t,; ]+"))
                    .filter(value -> !value.isBlank()).mapToDouble(Double::parseDouble).toArray();
                for (int i = 1; i + 1 < values.length; i += 2) {
                    if (values[i] >= 0 && values[i] <= 180 && values[i+1] >= 0) {
                        output.add(new Models.PolarPoint(values[0], values[i], values[i+1]));
                    }
                }
            } catch (RuntimeException badLine) {
                // One malformed polar line is ignored; all other valid lines survive.
            }
        }
        if (output.isEmpty()) throw new IllegalArgumentException("No valid polar triplets were found");
        return output;
    }

    /** Event CSV parser with repeatable/dynamic headers and short-row safety. */
    private static List<Models.ExpeditionEvent> parseEvents(byte[] raw) throws IOException {
        ArrayList<Models.ExpeditionEvent> output = new ArrayList<>();
        Map<String,Integer> header = new HashMap<>();
        int malformed = 0;
        try (CSVParser parser = CSVFormat.DEFAULT.builder().setTrim(true).setIgnoreEmptyLines(true)
                .get().parse(new StringReader(decode(raw)))) {
            Iterator<CSVRecord> iterator = parser.iterator();
            while (true) {
                CSVRecord record;
                try {
                    if (!iterator.hasNext()) break;
                    record = iterator.next();
                } catch (RuntimeException fatalRecord) {
                    System.err.println("Event CSV stopped after an unrecoverable record; " +
                        output.size() + " valid events retained: " + fatalRecord.getMessage());
                    break;
                }
                try {
                    Map<String,Integer> possibleHeader = eventHeader(record);
                    if (!possibleHeader.isEmpty()) {
                        header = possibleHeader; // repeated header or changed columns
                        continue;
                    }
                    if (header.isEmpty() || record.size() == 0) continue;
                    String rawTime = firstPresent(record, header, "time", "utc", "timestamp", "datetime");
                    LocalDateTime time = parseDateTime(typed(rawTime));
                    if (time == null) { malformed++; continue; }
                    String type = firstPresent(record, header, "type", "event type");
                    String comment = firstPresent(record, header, "comment", "event", "description");
                    output.add(new Models.ExpeditionEvent(time, type, comment));
                } catch (RuntimeException badRow) {
                    malformed++;
                }
            }
        }
        if (malformed > 0) {
            System.err.printf(Locale.ROOT, "Event CSV: retained %,d valid rows and skipped %,d malformed/short rows.%n",
                output.size(), malformed);
        }
        if (output.isEmpty()) throw new IllegalArgumentException("No valid Expedition event rows were found");
        return output;
    }

    private static Map<String,Integer> eventHeader(CSVRecord record) {
        HashMap<String,Integer> candidate = new HashMap<>();
        for (int i = 0; i < record.size(); i++) {
            String name = normalise(stripHeaderMarker(clean(record.get(i))));
            if (!name.isBlank()) candidate.put(name, i);
        }
        boolean hasTime = candidate.containsKey("time") || candidate.containsKey("utc") ||
            candidate.containsKey("timestamp") || candidate.containsKey("datetime");
        boolean hasEventContent = candidate.containsKey("type") || candidate.containsKey("event type") ||
            candidate.containsKey("comment") || candidate.containsKey("event") || candidate.containsKey("description");
        return hasTime && hasEventContent ? candidate : Map.of();
    }

    private static String firstPresent(CSVRecord record, Map<String,Integer> header, String... names) {
        for (String name : names) {
            Integer index = header.get(name);
            if (index != null && index >= 0 && index < record.size()) return clean(record.get(index));
        }
        return "";
    }

    private static List<Models.EventDefinition> parseEventList(byte[] raw) {
        ArrayList<Models.EventDefinition> output = new ArrayList<>();
        for (String line : decode(raw).split("\\R")) {
            if (line.isBlank() || line.stripLeading().startsWith("!")) continue;
            String[] parts = line.split(",", 3);
            if (parts.length < 3) continue;
            try {
                output.add(new Models.EventDefinition(
                    LocalDate.parse(unquote(parts[0].trim()), DateTimeFormatter.BASIC_ISO_DATE),
                    unquote(parts[1].trim()), unquote(parts[2].trim())));
            } catch (RuntimeException badRow) {
                // Only the malformed event-list row is discarded.
            }
        }
        if (output.isEmpty()) throw new IllegalArgumentException("No valid event-list rows were found");
        return output;
    }

    private static List<Models.SailPoint> parseSails(byte[] raw) throws Exception {
        ArrayList<Models.SailPoint> output = new ArrayList<>();
        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        try { factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true); }
        catch (Exception ignored) {}
        Document document = factory.newDocumentBuilder().parse(new ByteArrayInputStream(raw));
        NodeList elements = document.getElementsByTagName("element");
        for (int i = 0; i < elements.getLength(); i++) {
            try {
                Element element = (Element) elements.item(i);
                if (!"Sail".equals(element.getAttribute("type"))) continue;
                String colour = "#ffffff"; double opacity = .4, width = 3;
                NodeList colours = element.getElementsByTagName("colour");
                if (colours.getLength() > 0) {
                    Element c = (Element) colours.item(0);
                    colour = String.format("#%02x%02x%02x", attrInt(c,"r",255),
                        attrInt(c,"g",255), attrInt(c,"b",255));
                }
                NodeList opacityNodes = element.getElementsByTagName("shapeopacity");
                if (opacityNodes.getLength() > 0) opacity = attrDouble((Element)opacityNodes.item(0),"val",40)/100.0;
                NodeList widthNodes = element.getElementsByTagName("linewidth");
                if (widthNodes.getLength() > 0) width = attrDouble((Element)widthNodes.item(0),"val",3);
                NodeList points = element.getElementsByTagName("point");
                for (int j = 0; j < points.getLength(); j++) {
                    Element point = (Element) points.item(j);
                    output.add(new Models.SailPoint(element.getAttribute("name"), j+1,
                        attrDouble(point,"tws",0), attrDouble(point,"twa",0), colour, opacity, width));
                }
            } catch (RuntimeException badSail) {
                // One malformed sail element does not discard the remaining chart.
            }
        }
        if (output.isEmpty()) throw new IllegalArgumentException("No valid sail-chart points were found");
        return output;
    }

    private static String parseDebrief(MultipartFile file) throws Exception {
        if (file.getOriginalFilename() != null &&
                file.getOriginalFilename().toLowerCase(Locale.ROOT).endsWith(".docx")) {
            try (XWPFDocument document = new XWPFDocument(file.getInputStream())) {
                return document.getParagraphs().stream().map(paragraph -> paragraph.getText())
                    .filter(text -> !text.isBlank()).collect(Collectors.joining("\n\n"));
            }
        }
        return decode(file.getBytes());
    }

    private static Object typed(String raw) {
        if (raw == null || raw.isBlank()) return null;
        String value = raw.trim();
        try {
            double number = Double.parseDouble(value);
            return Double.isFinite(number) ? number : null;
        } catch (NumberFormatException ignored) {
            return value;
        }
    }

    private static Double number(Object value) {
        return value instanceof Number numeric ? numeric.doubleValue() : null;
    }

    /** Accepts Excel serials as Number or numeric String and rounds to one second. */
    static LocalDateTime parseDateTime(Object input) {
        if (input == null) return null;
        if (input instanceof Number number) return excelSerialToDateTime(number.doubleValue());
        String text = input.toString().trim();
        if (text.isEmpty()) return null;

        try {
            double serial = Double.parseDouble(text);
            if (Double.isFinite(serial) && serial >= 1.0 && serial <= 100_000.0) {
                return excelSerialToDateTime(serial);
            }
        } catch (NumberFormatException ignored) {}

        List<DateTimeFormatter> formatters = List.of(
            DateTimeFormatter.ISO_LOCAL_DATE_TIME,
            flexibleDateTimeFormatter("d/M/uuuu"),
            flexibleDateTimeFormatter("d-M-uuuu"),
            flexibleDateTimeFormatter("uuuu-M-d")
        );
        for (DateTimeFormatter formatter : formatters) {
            try { return roundToSecond(LocalDateTime.parse(text, formatter)); }
            catch (DateTimeParseException ignored) {}
        }
        try { return roundToSecond(OffsetDateTime.parse(text).toLocalDateTime()); }
        catch (DateTimeParseException ignored) { return null; }
    }

    private static DateTimeFormatter flexibleDateTimeFormatter(String datePattern) {
        return new DateTimeFormatterBuilder().parseCaseInsensitive()
            .appendPattern(datePattern + " H:mm[:ss]")
            .optionalStart()
            .appendFraction(java.time.temporal.ChronoField.NANO_OF_SECOND, 0, 9, true)
            .optionalEnd()
            .toFormatter(Locale.UK);
    }

	private static LocalDateTime excelSerialToDateTime(double serialDays) {
		if (!Double.isFinite(serialDays)
				|| serialDays < 0.0
				|| serialDays > 100_000.0) {
			return null;
		}

		long seconds = Math.round(serialDays * 86400.0);

		return LocalDateTime.of(1899, 12, 30, 0, 0)
				.plusSeconds(seconds);
	}

    private static LocalDateTime roundToSecond(LocalDateTime value) {
        return value.plusNanos(500_000_000L).truncatedTo(ChronoUnit.SECONDS);
    }

    private static String decode(byte[] raw) {
        return new String(raw, StandardCharsets.UTF_8).replace("\uFEFF", "");
    }
    private static String normalise(String value) {
        return value == null ? "" : value.trim().toLowerCase(Locale.ROOT)
            .replaceAll("[^a-z0-9]+", " ").trim();
    }
    private static String unquote(String value) { return value.replaceAll("^\\\"|\\\"$", ""); }
    private static int attrInt(Element element,String name,int fallback) {
        try { return Integer.parseInt(element.getAttribute(name)); } catch (Exception ex) { return fallback; }
    }
    private static double attrDouble(Element element,String name,double fallback) {
        try { return Double.parseDouble(element.getAttribute(name)); } catch (Exception ex) { return fallback; }
    }
    private static String blankToNull(String value) { return value == null || value.isBlank() ? null : value; }
    private static LocalDate parseDate(String value) {
        try { return value == null || value.isBlank() ? null : LocalDate.parse(value); }
        catch (Exception ex) { return null; }
    }
    private static LocalTime parseTime(String value, LocalTime fallback) {
        try { return value == null || value.isBlank() ? fallback : LocalTime.parse(value); }
        catch (Exception ex) { return fallback; }
    }
}
