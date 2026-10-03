package com.nightjar.analysis;
import java.util.*;
final class Models {
 private Models(){}
 record FilterRequest(List<String> events,String fromDate,String toDate,String startTime,String endTime,boolean trimByTime,List<String> includedVariables){}
 record DataResponse(List<Map<String,Object>> rows,List<String> warnings,int sourceRows,int matchedRows,int returnedRows,boolean plotDownsamplingApplied,Map<String,String> mapping){}
 record SettingsRequest(List<String> includedVariables,Map<String,String> mapping,Boolean plotDownsamplingEnabled,Integer maxPlotPoints){}
}
