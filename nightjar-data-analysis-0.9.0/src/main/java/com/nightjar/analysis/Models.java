package com.nightjar.analysis;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.*;

final class Models {
    private Models() {}

    record EventDefinition(LocalDate date, String type, String event) {}
    record ExpeditionEvent(LocalDateTime utcTime, String type, String comment) {}
    record PolarPoint(double tws, double twa, double targetBsp) {}
    record SailPoint(String sail, int order, double tws, double twa, String colour, double opacity, double width) {}

    static final class Row {
        LocalDateTime timestamp;
        final LinkedHashMap<String, Object> values = new LinkedHashMap<>();
        Map<String, Object> toMap(Set<String> included, String timeColumn) {
            LinkedHashMap<String, Object> out = new LinkedHashMap<>();
            if (timeColumn != null && included.contains(timeColumn) && timestamp != null) out.put(timeColumn, timestamp);
            values.forEach((key, value) -> { if (included.contains(key) && !Objects.equals(key, timeColumn)) out.put(key, value); });
            return out;
        }
    }

    record FilterRequest(List<String> events, String fromDate, String toDate, String startTime,
                         String endTime, boolean trimByTime, List<String> includedVariables) {}

    record DataResponse(List<Map<String,Object>> rows, List<String> warnings, int sourceRows,
                        int returnedRows, Map<String,String> mapping) {}

    record SettingsRequest(List<String> includedVariables, Map<String,String> mapping) {}
}
