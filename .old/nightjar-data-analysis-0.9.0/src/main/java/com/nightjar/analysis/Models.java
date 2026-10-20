package com.nightjar.analysis;
import java.time.*;
import java.util.*;
import java.util.function.BiConsumer;
final class Models {
 private Models(){}
 record EventDefinition(LocalDate date,String type,String event){}
 record ExpeditionEvent(LocalDateTime utcTime,String type,String comment){}
 record PolarPoint(double tws,double twa,double targetBsp){}
 record SailPoint(String sail,int order,double tws,double twa,String colour,double opacity,double width){}
 static final class CompactValues {
  private String[] keys; private Object[] values; private int size;
  CompactValues(int expected){int n=Math.max(4,expected);keys=new String[n];values=new Object[n];}
  Object get(String key){if(key==null)return null;for(int i=0;i<size;i++)if(keys[i].equals(key))return values[i];return null;}
  void put(String key,Object value){if(key==null||key.isBlank()||value==null)return;for(int i=0;i<size;i++)if(keys[i].equals(key)){values[i]=value;return;}if(size==keys.length){int n=keys.length+Math.max(4,keys.length/2);keys=Arrays.copyOf(keys,n);values=Arrays.copyOf(values,n);}keys[size]=key;values[size]=value;size++;}
  void forEach(BiConsumer<String,Object> action){for(int i=0;i<size;i++)action.accept(keys[i],values[i]);}
 }
 static final class Row {
  LocalDateTime timestamp; final CompactValues values;
  Row(int expected){values=new CompactValues(expected);}
  Map<String,Object> toMap(Set<String> included,String ts){LinkedHashMap<String,Object> out=new LinkedHashMap<>();if(ts!=null&&included.contains(ts)&&timestamp!=null)out.put(ts,timestamp);values.forEach((k,v)->{if(included.contains(k)&&!Objects.equals(k,ts))out.put(k,v);});return out;}
 }
 record FilterRequest(List<String> events,String fromDate,String toDate,String startTime,String endTime,boolean trimByTime,List<String> includedVariables){}
 record DataResponse(List<Map<String,Object>> rows,List<String> warnings,int sourceRows,int matchedRows,int returnedRows,boolean plotDownsamplingApplied,Map<String,String> mapping){}
 record SettingsRequest(List<String> includedVariables,Map<String,String> mapping,Boolean plotDownsamplingEnabled,Integer maxPlotPoints){}
}
