package com.nightjar.analysis;

import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVParser;
import org.apache.commons.csv.CSVRecord;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.StringReader;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeFormatterBuilder;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Locale;
import java.util.regex.Pattern;

/**
 * Parser for Expedition EventData.csv exports.
 *
 * Expedition can write AIS warning details on physical continuation lines even
 * though the Comment field is not CSV-quoted. Comments can also contain bare
 * commas. A conventional CSV parser therefore sees false records or too many
 * columns. This parser first reconstructs logical event records, then parses
 * the first physical line as CSV and appends continuation lines to Comment.
 */
final class EventDataParser {
    private static final Pattern EVENT_START = Pattern.compile(
        "^\\s*\\d{1,2}-[A-Za-z]{3}-\\d{4}\\s+" +
        "\\d{1,2}:\\d{2}(?::\\d{2})?\\s*,.*$"
    );

    private static final DateTimeFormatter EVENT_TIME =
        new DateTimeFormatterBuilder()
            .parseCaseInsensitive()
            .appendPattern("d-MMM-uuuu H:mm[:ss]")
            .toFormatter(Locale.UK);

    record ParseResult(List<Models.ExpeditionEvent> events,
                       List<String> warnings,
                       int physicalLines,
                       int logicalRecords,
                       int continuationLines) {}

    private EventDataParser() {}

    static ParseResult parse(byte[] raw) throws IOException {
        String text = decode(raw);
        List<String> header = Collections.emptyList();
        List<Models.ExpeditionEvent> events = new ArrayList<>();
        List<String> warnings = new ArrayList<>();

        String firstLine = null;
        List<String> continuation = new ArrayList<>();
        int physicalLines = 0;
        int logicalRecords = 0;
        int continuationLines = 0;

        try (BufferedReader reader = new BufferedReader(new StringReader(text))) {
            String line;
            boolean headerRead = false;
            while ((line = reader.readLine()) != null) {
                physicalLines++;
                if (!headerRead) {
                    if (line.isBlank()) continue;
                    header = csvFields(line);
                    headerRead = true;
                    continue;
                }

                if (EVENT_START.matcher(line).matches()) {
                    if (firstLine != null) {
                        logicalRecords++;
                        addRecord(events, warnings, header, firstLine, continuation, logicalRecords);
                    }
                    firstLine = line;
                    continuation = new ArrayList<>();
                } else if (!line.isBlank() && firstLine != null) {
                    // Expedition AIS/CPA details are emitted as unquoted physical
                    // lines. They belong to the preceding event's Comment field.
                    continuation.add(line);
                    continuationLines++;
                } else if (!line.isBlank()) {
                    warnings.add("Ignored content before the first event at physical line " + physicalLines);
                }
            }
        }

        if (firstLine != null) {
            logicalRecords++;
            addRecord(events, warnings, header, firstLine, continuation, logicalRecords);
        }
        if (header.isEmpty()) warnings.add("Event file has no header row.");

        return new ParseResult(
            List.copyOf(events), List.copyOf(warnings), physicalLines,
            logicalRecords, continuationLines
        );
    }

    private static void addRecord(List<Models.ExpeditionEvent> events,
                                  List<String> warnings,
                                  List<String> header,
                                  String firstLine,
                                  List<String> continuation,
                                  int logicalRecordNumber) throws IOException {
        List<String> fields = csvFields(firstLine);
        int timeIndex = indexOf(header, "Time", 0);
        int typeIndex = indexOf(header, "Type", 9);
        int commentIndex = indexOf(header, "Comment", 11);

        String rawTime = field(fields, timeIndex).strip();
        LocalDateTime utcTime;
        try {
            utcTime = LocalDateTime.parse(rawTime, EVENT_TIME);
        } catch (DateTimeParseException ex) {
            warnings.add("Skipped logical event " + logicalRecordNumber +
                ": invalid Time value '" + rawTime + "'.");
            return;
        }

        String type = field(fields, typeIndex).strip();
        StringBuilder comment = new StringBuilder();

        // A bare comma in Comment creates extra CSV fields. Rejoin every field
        // from Comment onwards so no user-entered text is lost.
        for (int i = commentIndex; i < fields.size(); i++) {
            if (i > commentIndex) comment.append(',');
            comment.append(fields.get(i));
        }
        for (String extraLine : continuation) {
            if (!comment.isEmpty()) comment.append('\n');
            comment.append(extraLine);
        }

        events.add(new Models.ExpeditionEvent(utcTime, type, comment.toString()));
    }

    private static List<String> csvFields(String line) throws IOException {
        try (CSVParser parser = CSVParser.parse(line, CSVFormat.DEFAULT)) {
            var iterator = parser.iterator();
            CSVRecord record = iterator.hasNext() ? iterator.next() : null;
            if (record == null) return Collections.emptyList();
            List<String> values = new ArrayList<>(record.size());
            for (String value : record) values.add(value == null ? "" : value);
            return values;
        }
    }

    private static int indexOf(List<String> header, String wanted, int fallback) {
        for (int i = 0; i < header.size(); i++) {
            if (wanted.equalsIgnoreCase(header.get(i).strip())) return i;
        }
        return fallback;
    }

    private static String field(List<String> fields, int index) {
        return index >= 0 && index < fields.size() ? fields.get(index) : "";
    }

    private static String decode(byte[] raw) {
        String value = new String(raw, StandardCharsets.UTF_8);
        return value.startsWith("\uFEFF") ? value.substring(1) : value;
    }
}
