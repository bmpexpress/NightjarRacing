package com.nightjar.analysis;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.*;
import java.util.function.BiConsumer;

final class Models {
    private Models() {}

    record EventDefinition(LocalDate date, String type, String event) {}
    record ExpeditionEvent(LocalDateTime utcTime, String type, String comment) {}
    record PolarPoint(double tws, double twa, double targetBsp) {}
    record SailPoint(String sail, int order, double tws, double twa, String colour, double opacity, double width) {}

    /**
     * Compact per-row sparse storage. Unlike HashMap/LinkedHashMap this allocates no
     * hash table, nodes or Entry objects. Channel-name String instances are shared.
     */
    static final class CompactValues {
        private String[] keys;
        private Object[] values;
        private int size;

        CompactValues(int expectedValues) {
            int capacity = Math.max(4, expectedValues);
            keys = new String[capacity];
            values = new Object[capacity];
        }

        Object get(String key) {
            if (key == null) return null;
            for (int i = 0; i < size; i++) if (keys[i].equals(key)) return values[i];
            return null;
        }

        void put(String key, Object value) {
            if (key == null || value == null) return; // Missing sparse values cost no heap.
            for (int i = 0; i < size; i++) {
                if (keys[i].equals(key)) { values[i] = value; return; }
            }
            if (size == keys.length) {
                int next = keys.length + Math.max(4, keys.length / 2);
                keys = Arrays.copyOf(keys, next);
                values = Arrays.copyOf(values, next);
            }
            keys[size] = key;
            values[size] = value;
            size++;
        }

        void forEach(BiConsumer<String,Object> action) {
            for (int i = 0; i < size; i++) action.accept(keys[i], values[i]);
        }
    }

    static final class Row {
        LocalDateTime timestamp;
        final CompactValues values;
        Row(int expectedValues) { values = new CompactValues(expectedValues); }

        Map<String, Object> toMap(Set<String> included, String timeColumn) {
            LinkedHashMap<String, Object> out = new LinkedHashMap<>();
            if (timeColumn != null && included.contains(timeColumn) && timestamp != null) {
                out.put(timeColumn, timestamp);
            }
            values.forEach((key, value) -> {
                if (included.contains(key) && !Objects.equals(key, timeColumn)) out.put(key, value);
            });
            return out;
        }
    }

    record FilterRequest(List<String> events, String fromDate, String toDate, String startTime,
                         String endTime, boolean trimByTime, List<String> includedVariables) {}
    record DataResponse(List<Map<String,Object>> rows, List<String> warnings, int sourceRows,
                        int returnedRows, Map<String,String> mapping) {}
    record SettingsRequest(List<String> includedVariables, Map<String,String> mapping) {}
}
