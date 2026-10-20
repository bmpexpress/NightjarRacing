package com.nightjar.analysis;
import static org.junit.jupiter.api.Assertions.*;
import java.io.*;import java.nio.charset.StandardCharsets;import java.time.*;import java.util.*;import org.junit.jupiter.api.Test;
class DataStoreTest {
 @Test void roundsSmallExcelSerialToNearestSecond(){assertEquals(LocalDateTime.of(1899,12,30,0,0,1),DataStore.parseDateTime(0.6/86400.0));}
 @Test void convertsGunUtcUsingBstRules(){assertEquals(LocalDateTime.of(2026,7,1,13,0),DataStore.gunLocal(LocalDateTime.of(2026,7,1,12,0)));assertEquals(LocalDateTime.of(2026,12,1,12,0),DataStore.gunLocal(LocalDateTime.of(2026,12,1,12,0)));}
 @Test void changingSparseHeadersAndBadRowsRetainValidRows()throws Exception{String text=String.join("\n","!Boat,Utc,BSP,TWA","!Boat,0,101,102","0,46285.500000,101,8.2,102,42","0,bad-time,101,9","one field","!Boat,Utc,BSP,TWA,Heel","!Boat,0,101,102,207,","0,46285.500012,101,8.4,102,43,207,12.1","0,46285.500023,101,8.5,999,123","1,46285.6,101,99","");DataStore store=new DataStore();store.parseLog(new ByteArrayInputStream(text.getBytes(StandardCharsets.UTF_8)));Map<String,Object>state=store.state();assertEquals(3,state.get("rowCount"));assertTrue(((Set<?>)state.get("columns")).contains("Heel"));}
 @Test void vmgPercentAliasPrefersExpeditionVmgPercent()throws Exception{String csv="Boat,Utc,BSP,TWA,VMG%\n0,46285,8,40,92\n";DataStore store=new DataStore();store.parseLog(new ByteArrayInputStream(csv.getBytes(StandardCharsets.UTF_8)));assertEquals("VMG%",((Map<?,?>)store.state().get("mapping")).get("vmg_pct"));}
}
