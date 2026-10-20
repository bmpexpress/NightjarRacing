package com.nightjar.analysis;

import static org.junit.jupiter.api.Assertions.*;

import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.util.Map;

import org.junit.jupiter.api.Test;

class DataStoreResilientLoaderTest {

    @Test
    void numericStringExcelDateIsAcceptedAndRounded() {
        LocalDateTime expected = LocalDateTime.of(1970, 1, 1, 12, 0, 1);
        assertEquals(expected, DataStore.parseDateTime("25569.500006944444"));
    }

    @Test
    void sparseLogHandlesRepeatedChangingHeadersAndSkipsOnlyBadRows() throws Exception {
        String source = String.join("\n",
            "!Boat,Utc,BSP,TWA",
            "!Boat,0,101,102",
            "0,46285.500000,101,8.2,102,42",
            "0,not-a-date,101,99,102,99",
            "this malformed row has one field",
            "!Boat,Utc,BSP,TWA,Heel,Latitude",
            "!Boat,0,101,102,207,301,",
            "0,46285.500012,101,8.4,102,43,207,12.1,301,50.7",
            "0,46285.500023,101,8.5,999,123,207,12.2",
            "1,46285.500034,101,50",
            "");

        DataStore store = new DataStore();
        store.parseLog(new ByteArrayInputStream(source.getBytes(StandardCharsets.UTF_8)));

        Map<String, Object> state = store.state();

        assertEquals(3, state.get("rowCount"));
        assertTrue(((java.util.Set<?>) state.get("columns")).contains("Heel"));

        assertTrue(
            ((java.util.List<?>) state.get("loadWarnings")).stream()
                .anyMatch(value -> {
                    String text = value.toString().toLowerCase();
                    return text.contains("invalid");
                }),
            "Expected an invalid timestamp warning, but loadWarnings was: "
                + state.get("loadWarnings")
        );
    }

    @Test
    void bstConversionStillUsesEuropeLondonRules() {
        assertEquals(
            LocalDateTime.of(2026, 7, 1, 13, 0),
            DataStore.gunLocal(LocalDateTime.of(2026, 7, 1, 12, 0))
        );

        assertEquals(
            LocalDateTime.of(2026, 12, 1, 12, 0),
            DataStore.gunLocal(LocalDateTime.of(2026, 12, 1, 12, 0))
        );
    }
}