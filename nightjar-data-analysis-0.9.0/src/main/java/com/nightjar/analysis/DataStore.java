package com.nightjar.analysis;

import org.apache.commons.csv.*;
import org.apache.poi.xwpf.usermodel.XWPFDocument;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import org.w3c.dom.*;
import jakarta.annotation.PostConstruct;
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

    private static final ZoneId DATA_ZONE = ZoneId.of("Europe/London");
    private static final ZoneId GUN_ZONE = ZoneOffset.UTC;
    private static final Map<String,List<String>> ALIASES = Map.ofEntries(
        Map.entry("timestamp", List.of("utc","time","timestamp","datetime")),
        Map.entry("bsp", List.of("bsp","boat speed","log bsp")),
        Map.entry("twa", List.of("twa","true wind angle")),
        Map.entry("tws", List.of("tws","true wind speed")),
        Map.entry("awa", List.of("awa","apparent wind angle")),
        Map.entry("aws", List.of("aws")), Map.entry("vmg", List.of("vmg","velocity made good","vmg kt","vmg knots")),
        Map.entry("vmg_pct", List.of("vmg%","vmg %","vmg pct","vmg percent")),
        Map.entry("heel", List.of("heel")), Map.entry("drift", List.of("drift","tide rate")),
        Map.entry("lat", List.of("lat","latitude","lat1")), Map.entry("lon", List.of("lon","longitude","lon1")),
        Map.entry("sog", List.of("sog")), Map.entry("cog", List.of("cog")), Map.entry("sail", List.of("sail","foresail_id","foresail"))
    );

    @PostConstruct
    void loadDefaultData() {
        Path data = Path.of(System.getenv().getOrDefault("NIGHTJAR_DATA_DIR", "/Data"));
        lock.writeLock().lock();
        try {
            if (Files.exists(data.resolve("logfile.csv"))) parseLog(Files.readAllBytes(data.resolve("logfile.csv")));
            if (Files.exists(data.resolve("Polar.txt"))) polar = parsePolar(Files.readAllBytes(data.resolve("Polar.txt")));
            if (Files.exists(data.resolve("EventData.csv"))) expeditionEvents = parseEvents(Files.readAllBytes(data.resolve("EventData.csv")));
            if (Files.exists(data.resolve("EventList.txt"))) eventList = parseEventList(Files.readAllBytes(data.resolve("EventList.txt")));
            if (Files.exists(data.resolve("SailChart.xml"))) sails = parseSails(Files.readAllBytes(data.resolve("SailChart.xml")));
            addCalculatedVmgPct();
        } catch (Exception ex) {
            System.err.println("Nightjar default data was not loaded: " + ex.getMessage());
        } finally { lock.writeLock().unlock(); }
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
            state.put("gunEvents", expeditionEvents.stream().filter(e -> e.utcTime() != null && isGun(e)).map(e -> Map.of(
                "utc", e.utcTime(), "local", e.utcTime() == null ? "" : gunLocal(e.utcTime()),
                "type", e.type() == null ? "" : e.type(), "comment", e.comment() == null ? "" : e.comment()
            )).toList());
            state.put("debrief", debrief);
            state.put("dataTimeZone", DATA_ZONE.getId());
            state.put("gunTimeZone", GUN_ZONE.getId());
            return state;
        } finally { lock.readLock().unlock(); }
    }

    public void upload(MultipartFile log, MultipartFile polarFile, MultipartFile events,
                       MultipartFile eventListFile, MultipartFile sailChart, MultipartFile debriefFile) throws Exception {
        lock.writeLock().lock();
        try {
            if (log != null && !log.isEmpty()) parseLog(log.getBytes());
            if (polarFile != null && !polarFile.isEmpty()) polar = parsePolar(polarFile.getBytes());
            if (events != null && !events.isEmpty()) expeditionEvents = parseEvents(events.getBytes());
            if (eventListFile != null && !eventListFile.isEmpty()) eventList = parseEventList(eventListFile.getBytes());
            if (sailChart != null && !sailChart.isEmpty()) sails = parseSails(sailChart.getBytes());
            if (debriefFile != null && !debriefFile.isEmpty()) debrief = parseDebrief(debriefFile);
            addCalculatedVmgPct();
        } finally { lock.writeLock().unlock(); }
    }

    public void updateSettings(Models.SettingsRequest request) {
        lock.writeLock().lock();
        try {
            LinkedHashSet<String> wanted = request.includedVariables() == null
                ? new LinkedHashSet<>(columns)
                : request.includedVariables().stream().filter(columns::contains)
                    .collect(Collectors.toCollection(LinkedHashSet::new));
            included = wanted;
            if (request.mapping() != null) {
                request.mapping().forEach((key,value) -> {
                    if (value == null || value.isBlank() || columns.contains(value)) mapping.put(key, blankToNull(value));
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
            Set<LocalDate> selectedDates = eventList.stream().filter(e -> selectedEvents.contains(e.event()))
                .map(Models.EventDefinition::date).collect(Collectors.toSet());
            LocalDate from = parseDate(request.fromDate());
            LocalDate to = parseDate(request.toDate());
            LocalTime start = parseTime(request.startTime(), LocalTime.MIN);
            LocalTime end = parseTime(request.endTime(), LocalTime.MAX.truncatedTo(ChronoUnit.SECONDS));
            List<String> warnings = new ArrayList<>();
            Map<LocalDate,LocalDateTime> gunCutoffs = gunCutoffs(selectedDates, warnings);
            ArrayList<Map<String,Object>> result = new ArrayList<>();
            for (Models.Row row : rows) {
                LocalDateTime stamp = row.timestamp;
                if (stamp == null) continue;
                LocalDate day = stamp.toLocalDate();
                if (!selectedDates.isEmpty() && !selectedDates.contains(day)) continue;
                if (selectedDates.isEmpty()) {
                    if (from != null && day.isBefore(from)) continue;
                    if (to != null && day.isAfter(to)) continue;
                }
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
            if (gun.isEmpty()) warnings.add("No GUN entry found for " + date + ". Filter this event manually if required.");
            else output.put(date, gunLocal(gun.get().utcTime()).minusMinutes(5));
        }
        return output;
    }

    private static boolean isGun(Models.ExpeditionEvent e) {
        return ((e.type() == null ? "" : e.type()) + " " + (e.comment() == null ? "" : e.comment()))
            .toLowerCase(Locale.ROOT).contains("gun");
    }

    // Expedition event timestamps are UTC. The log is displayed as Europe/London local time.
    // ZoneRules applies +01:00 only during BST and +00:00 during GMT, including transition dates.
    static LocalDateTime gunLocal(LocalDateTime utc) {
        return utc.atZone(GUN_ZONE).withZoneSameInstant(DATA_ZONE).toLocalDateTime();
    }

    private void parseLog(byte[] raw) throws IOException {
        String text = decode(raw);
        List<Models.Row> parsed = text.stripLeading().startsWith("!") ? parseSparseLog(text) : parseStandardLog(text);
        if (parsed.isEmpty()) throw new IllegalArgumentException("The log file is empty or could not be parsed");
        rows = parsed;
        columns = new LinkedHashSet<>();
        rows.forEach(r -> columns.addAll(r.values.keySet()));
        mapping = detectMappings(columns);
        String ts = mapping.get("timestamp");
        for (Models.Row row : rows) row.timestamp = parseDateTime(row.values.get(ts));
        rows.removeIf(r -> r.timestamp == null);
        rows.sort(Comparator.comparing(r -> r.timestamp));
        addCalculatedVmg();
        included = new LinkedHashSet<>(columns);
    }

    private List<Models.Row> parseStandardLog(String text) throws IOException {
        CSVFormat format = CSVFormat.DEFAULT.builder().setHeader().setSkipHeaderRecord(true)
            .setIgnoreEmptyLines(true).setTrim(true).get();
        ArrayList<Models.Row> out = new ArrayList<>();
        try (CSVParser parser = format.parse(new StringReader(text))) {
            for (CSVRecord record : parser) {
                if (record.isMapped("Boat") && !"0".equals(record.get("Boat").trim())) continue;
                Models.Row row = new Models.Row();
                for (String header : parser.getHeaderNames()) row.values.put(header, typed(record.isMapped(header) ? record.get(header) : null));
                out.add(row);
            }
        }
        return out;
    }

    private List<Models.Row> parseSparseLog(String text) throws IOException {
        ArrayList<Models.Row> out = new ArrayList<>();
        List<String> names = null;
        Map<String,String> lookup = new HashMap<>();
        try (CSVParser parser = CSVFormat.DEFAULT.parse(new StringReader(text))) {
            for (CSVRecord rec : parser) {
                if (rec.size() == 0) continue;
                String first = rec.get(0).trim();
                String second = rec.size() > 1 ? rec.get(1).trim() : "";
                if ("!boat".equalsIgnoreCase(first) && "utc".equalsIgnoreCase(second)) {
                    names = new ArrayList<>(); rec.forEach(names::add); lookup.clear(); continue;
                }
                if ("!boat".equalsIgnoreCase(first) && second.matches("[+-]?\\d+")) {
                    if (names != null && names.size() == rec.size()) {
                        for (int i=0;i<rec.size();i++) if (rec.get(i).trim().matches("[+-]?\\d+"))
                            lookup.put(rec.get(i).trim(), names.get(i).replaceFirst("^!", "").trim());
                    }
                    continue;
                }
                if (first.startsWith("!") || rec.size() < 2 || !"0".equals(first)) continue;
                Models.Row row = new Models.Row(); row.values.put("Boat", first); row.values.put("Utc", second);
                for (int i=2;i+1<rec.size();i+=2) {
                    String channel = lookup.get(rec.get(i).trim());
                    if (channel != null) row.values.put(channel, typed(rec.get(i+1)));
                }
                out.add(row);
            }
        }
        return out;
    }

    private void addCalculatedVmg() {
        String old = mapping.get("vmg"), bsp = mapping.get("bsp"), twa = mapping.get("twa");
        if (old != null || bsp == null || twa == null) return;
        for (Models.Row row : rows) {
            Double speed = number(row.values.get(bsp)), angle = number(row.values.get(twa));
            row.values.put("VMG", speed == null || angle == null ? null : speed * Math.cos(Math.toRadians(signedAngle(angle))));
        }
        columns.add("VMG"); mapping.put("vmg", "VMG");
    }

    private void addCalculatedVmgPct() {
        if (rows.isEmpty() || polar.isEmpty()) return;
        String existing = mapping.get("vmg_pct"), vmg = mapping.get("vmg"), tws = mapping.get("tws"), twa = mapping.get("twa");
        if (existing != null || vmg == null || tws == null || twa == null) return;
        Map<Double,List<Models.PolarPoint>> curves = polar.stream().collect(Collectors.groupingBy(Models.PolarPoint::tws));
        double[] winds = curves.keySet().stream().mapToDouble(Double::doubleValue).sorted().toArray();
        if (winds.length == 0) return;
        for (Models.Row row : rows) {
            Double actual=number(row.values.get(vmg)), wind=number(row.values.get(tws)), angle=number(row.values.get(twa));
            Double target=wind==null||angle==null?null:targetBsp(curves,winds,wind,Math.abs(signedAngle(angle)));
            double denominator=target==null?Double.NaN:Math.abs(target*Math.cos(Math.toRadians(Math.abs(signedAngle(angle)))));
            row.values.put("VMG_PCT", actual==null||!Double.isFinite(denominator)||denominator<.05?null:Math.abs(actual)/denominator*100.0);
        }
        columns.add("VMG_PCT"); mapping.put("vmg_pct","VMG_PCT"); included.add("VMG_PCT");
    }

    private static Double targetBsp(Map<Double,List<Models.PolarPoint>> curves,double[] winds,double tws,double twa) {
        if (tws < winds[0] || tws > winds[winds.length-1]) return null;
        int hi=Arrays.binarySearch(winds,tws); if(hi<0)hi=-hi-1;
        int lo=hi==0?0:hi-1; if(hi>=winds.length)hi=winds.length-1;
        Double low=angleInterpolate(curves.get(winds[lo]),twa), high=angleInterpolate(curves.get(winds[hi]),twa);
        if(low==null||high==null)return null; if(lo==hi)return low;
        double weight=(tws-winds[lo])/(winds[hi]-winds[lo]); return low+weight*(high-low);
    }
    private static Double angleInterpolate(List<Models.PolarPoint> points,double twa) {
        List<Models.PolarPoint> p=points.stream().sorted(Comparator.comparingDouble(Models.PolarPoint::twa)).toList();
        if(p.isEmpty()||twa<p.get(0).twa()||twa>p.get(p.size()-1).twa())return null;
        for(int i=0;i<p.size();i++){
            if(Math.abs(p.get(i).twa()-twa)<1e-9)return p.get(i).targetBsp();
            if(p.get(i).twa()>twa){Models.PolarPoint a=p.get(i-1),b=p.get(i);double w=(twa-a.twa())/(b.twa()-a.twa());return a.targetBsp()+w*(b.targetBsp()-a.targetBsp());}
        }
        return p.get(p.size()-1).targetBsp();
    }

    private static double signedAngle(double angle) { return ((angle + 180.0) % 360.0 + 360.0) % 360.0 - 180.0; }

    private static LinkedHashMap<String,String> detectMappings(Set<String> names) {
        LinkedHashMap<String,String> out = new LinkedHashMap<>();
        Map<String,String> normal = names.stream().collect(Collectors.toMap(DataStore::normalise, x -> x, (a,b)->a, LinkedHashMap::new));
        ALIASES.forEach((key, aliases) -> {
            String found = aliases.stream().map(DataStore::normalise).map(normal::get).filter(Objects::nonNull).findFirst().orElse(null);
            if (found == null) found = names.stream().filter(n -> aliases.stream().anyMatch(a -> normalise(n).startsWith(normalise(a)))).findFirst().orElse(null);
            out.put(key, found);
        });
        if (out.get("vmg") != null && (out.get("vmg").contains("%") || normalise(out.get("vmg")).contains("pct"))) out.put("vmg", null);
        return out;
    }

    private static List<Models.PolarPoint> parsePolar(byte[] raw) {
        ArrayList<Models.PolarPoint> out = new ArrayList<>();
        for (String line : decode(raw).split("\|R")) {
            line = line.trim(); if (line.isEmpty() || line.startsWith("!") || line.startsWith("#")) continue;
            try {
                double[] values = Arrays.stream(line.split("[\t,; ]+")).filter(s -> !s.isBlank()).mapToDouble(Double::parseDouble).toArray();
                for (int i=1;i+1<values.length;i+=2) if (values[i]>=0 && values[i]<=180 && values[i+1]>=0)
                    out.add(new Models.PolarPoint(values[0], values[i], values[i+1]));
            } catch (NumberFormatException ignored) {}
        }
        return out;
    }

    private static List<Models.EventDefinition> parseEventList(byte[] raw) {
        ArrayList<Models.EventDefinition> out = new ArrayList<>();
        for (String line : decode(raw).split("\\R")) {
            String[] p = line.split(",", 3); if (p.length < 3) continue;
            try { out.add(new Models.EventDefinition(LocalDate.parse(unquote(p[0].trim()), DateTimeFormatter.BASIC_ISO_DATE), unquote(p[1].trim()), unquote(p[2].trim()))); }
            catch (DateTimeParseException ignored) {}
        }
        return out;
    }

    private static List<Models.ExpeditionEvent> parseEvents(byte[] raw) throws IOException {
        ArrayList<Models.ExpeditionEvent> out = new ArrayList<>();
        CSVFormat format = CSVFormat.DEFAULT.builder().setHeader().setSkipHeaderRecord(true).setTrim(true).get();
        try (CSVParser parser = format.parse(new StringReader(decode(raw)))) {
            for (CSVRecord rec : parser) {
                LocalDateTime time = parseDateTime(rec.isMapped("Time") ? rec.get("Time") : null);
                String type = rec.isMapped("Type") ? rec.get("Type") : "";
                String comment = rec.isMapped("Comment") ? rec.get("Comment") : "";
                out.add(new Models.ExpeditionEvent(time, type, comment));
            }
        }
        return out;
    }

    private static List<Models.SailPoint> parseSails(byte[] raw) throws Exception {
        ArrayList<Models.SailPoint> out = new ArrayList<>();
        Document doc = DocumentBuilderFactory.newInstance().newDocumentBuilder().parse(new ByteArrayInputStream(raw));
        NodeList elements = doc.getElementsByTagName("element");
        for (int i=0;i<elements.getLength();i++) {
            Element e=(Element)elements.item(i); if (!"Sail".equals(e.getAttribute("type"))) continue;
            String colour="#ffffff"; double opacity=.4, width=3;
            NodeList colours=e.getElementsByTagName("colour");
            if (colours.getLength()>0) { Element c=(Element)colours.item(0); colour=String.format("#%02x%02x%02x", attrInt(c,"r",255),attrInt(c,"g",255),attrInt(c,"b",255)); }
            NodeList ops=e.getElementsByTagName("shapeopacity"); if(ops.getLength()>0) opacity=attrDouble((Element)ops.item(0),"val",40)/100.0;
            NodeList widths=e.getElementsByTagName("linewidth"); if(widths.getLength()>0) width=attrDouble((Element)widths.item(0),"val",3);
            NodeList points=e.getElementsByTagName("point");
            for(int j=0;j<points.getLength();j++){Element p=(Element)points.item(j); out.add(new Models.SailPoint(e.getAttribute("name"),j+1,attrDouble(p,"tws",0),attrDouble(p,"twa",0),colour,opacity,width));}
        }
        return out;
    }

    private static String parseDebrief(MultipartFile file) throws Exception {
        if (file.getOriginalFilename()!=null && file.getOriginalFilename().toLowerCase(Locale.ROOT).endsWith(".docx")) {
            try (XWPFDocument doc = new XWPFDocument(file.getInputStream())) {
                return doc.getParagraphs().stream().map(p -> p.getText()).filter(s -> !s.isBlank()).collect(Collectors.joining("\n\n"));
            }
        }
        return decode(file.getBytes());
    }

    private static Object typed(String raw) {
        if (raw == null || raw.isBlank()) return null;
        try { double d=Double.parseDouble(raw.trim()); return Double.isFinite(d)?d:null; }
        catch (NumberFormatException ignored) { return raw.trim(); }
    }
    private static Double number(Object value) { return value instanceof Number n ? n.doubleValue() : null; }
    private static String decode(byte[] raw) { return new String(raw, StandardCharsets.UTF_8).replace("\uFEFF", ""); }
    private static String normalise(String v) { return v == null ? "" : v.trim().toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9]+", " ").trim(); }
    private static String unquote(String v) { return v.replaceAll("^\"|\"$", ""); }
    private static int attrInt(Element e,String n,int d){try{return Integer.parseInt(e.getAttribute(n));}catch(Exception x){return d;}}
    private static double attrDouble(Element e,String n,double d){try{return Double.parseDouble(e.getAttribute(n));}catch(Exception x){return d;}}
    private static String blankToNull(String s) { return s == null || s.isBlank() ? null : s; }
    private static LocalDate parseDate(String s) { try { return s==null||s.isBlank()?null:LocalDate.parse(s); } catch(Exception e){return null;} }
    private static LocalTime parseTime(String s, LocalTime fallback) { try{return s==null||s.isBlank()?fallback:LocalTime.parse(s);}catch(Exception e){return fallback;} }

    static LocalDateTime parseDateTime(Object input) {
        if (input == null) return null;
        if (input instanceof Number n) {
            long seconds = Math.round(n.doubleValue() * 86400.0);
            return LocalDateTime.of(1899,12,30,0,0).plusSeconds(seconds);
        }
        String text=input.toString().trim(); if(text.isEmpty())return null;
        List<DateTimeFormatter> fmts=List.of(
            DateTimeFormatter.ISO_LOCAL_DATE_TIME,
            new DateTimeFormatterBuilder().parseCaseInsensitive().appendPattern("d/M/uuuu H:mm[:ss][.SSS]").toFormatter(Locale.UK),
            new DateTimeFormatterBuilder().parseCaseInsensitive().appendPattern("d-M-uuuu H:mm[:ss][.SSS]").toFormatter(Locale.UK),
            new DateTimeFormatterBuilder().parseCaseInsensitive().appendPattern("uuuu-M-d H:mm[:ss][.SSS]").toFormatter(Locale.UK)
        );
        for(DateTimeFormatter f:fmts)try{return LocalDateTime.parse(text,f);}catch(Exception ignored){}
        try { return OffsetDateTime.parse(text).toLocalDateTime(); } catch(Exception ignored) {}
        return null;
    }
}
