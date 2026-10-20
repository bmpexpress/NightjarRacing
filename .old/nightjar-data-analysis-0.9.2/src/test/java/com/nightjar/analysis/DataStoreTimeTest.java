package com.nightjar.analysis;

import static org.junit.jupiter.api.Assertions.assertEquals;
import java.time.LocalDateTime;
import org.junit.jupiter.api.Test;

class DataStoreTimeTest {
    @Test void convertsUtcGunToBstInSummer() {
        assertEquals(LocalDateTime.of(2026,7,1,13,0), DataStore.gunLocal(LocalDateTime.of(2026,7,1,12,0)));
    }
    @Test void keepsUtcGunAtGmtInWinter() {
        assertEquals(LocalDateTime.of(2026,12,1,12,0), DataStore.gunLocal(LocalDateTime.of(2026,12,1,12,0)));
    }
    @Test void roundsExcelTimestampToNearestSecond() {
        LocalDateTime base=LocalDateTime.of(1899,12,30,0,0);
        assertEquals(base.plusSeconds(1),DataStore.parseDateTime(0.6/86400.0));
    }
}
