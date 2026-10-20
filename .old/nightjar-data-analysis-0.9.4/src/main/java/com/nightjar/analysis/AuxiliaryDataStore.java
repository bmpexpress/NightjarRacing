package com.nightjar.analysis;
import org.apache.commons.csv.*;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.time.*;
import java.time.format.*;
import java.time.temporal.ChronoField;
import java.util.*;
@Service
public class AuxiliaryDataStore {
 private static final ZoneId DATA_ZONE=ZoneId.of("Europe/London");
 private volatile List<Map<String,Object>> eventData=List.of(),testData=List.of();
 public AuxiliaryDataStore(){reload();}
 public synchronized void reload(){Path dir=Path.of(System.getenv().getOrDefault("NIGHTJAR_DATA_DIR","/Data"));eventData=read(dir.resolve("EventData.csv"));testData=read(dir.resolve("TestData.csv"));}
 public synchronized void upload(MultipartFile eventFile,MultipartFile testFile){try{if(eventFile!=null&&!eventFile.isEmpty())eventData=parse(eventFile.getBytes());if(testFile!=null&&!testFile.isEmpty())testData=parse(testFile.getBytes());}catch(IOException e){throw new IllegalArgumentException("Unable to read Expedition data",e);}}
 public Map<String,Integer> counts(){return Map.of("eventData",eventData.size(),"testData",testData.size());}
 public List<Map<String,Object>> filtered(String source,List<String>eventDates,String fromDate,String toDate,String startTime,String endTime,boolean trimByTime){List<Map<String,Object>>rows="test".equalsIgnoreCase(source)?testData:eventData;Set<LocalDate>days=new HashSet<>();if(eventDates!=null)for(String value:eventDates)try{days.add(LocalDate.parse(value));}catch(Exception ignored){}LocalDate from=date(fromDate),to=date(toDate);LocalTime start=time(startTime,LocalTime.MIN),end=time(endTime,LocalTime.MAX.withNano(0));ArrayList<Map<String,Object>>out=new ArrayList<>();for(Map<String,Object>row:rows){LocalDateTime utc=timestamp(row);if(utc==null){if(days.isEmpty()&&from==null&&to==null)out.add(row);continue;}LocalDateTime local=utc.atZone(ZoneOffset.UTC).withZoneSameInstant(DATA_ZONE).toLocalDateTime();LocalDate day=local.toLocalDate();if(!days.isEmpty()&&!days.contains(day))continue;if(days.isEmpty()&&((from!=null&&day.isBefore(from))||(to!=null&&day.isAfter(to))))continue;if(trimByTime&&(local.toLocalTime().isBefore(start)||local.toLocalTime().isAfter(end)))continue;out.add(row);if(out.size()>=20_000)break;}return out;}
 private static List<Map<String,Object>>read(Path path){try{return Files.exists(path)?parse(Files.readAllBytes(path)):List.of();}catch(IOException e){return List.of();}}
 private static List<Map<String,Object>>parse(byte[]raw)throws IOException{ArrayList<Map<String,Object>>out=new ArrayList<>();List<String>headers=null;String text=new String(raw,StandardCharsets.UTF_8).replace("\uFEFF","");try(CSVParser parser=CSVFormat.DEFAULT.builder().setTrim(true).setIgnoreEmptyLines(true).get().parse(new StringReader(text))){for(CSVRecord record:parser){if(headers==null){headers=new ArrayList<>();for(String value:record)headers.add(value.replaceFirst("^!","").trim());continue;}LinkedHashMap<String,Object>row=new LinkedHashMap<>();for(int i=0;i<Math.min(headers.size(),record.size());i++)row.put(headers.get(i),typed(record.get(i)));out.add(row);}}return List.copyOf(out);}
 private static LocalDateTime timestamp(Map<String,Object>row){for(Map.Entry<String,Object>entry:row.entrySet()){String key=entry.getKey().toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9]+","");if(Set.of("utc","time","timestamp","datetime").contains(key)){LocalDateTime parsed=parseDateTime(entry.getValue());if(parsed!=null)return parsed;}}return null;}
 private static LocalDateTime parseDateTime(Object input){if(input==null)return null;if(input instanceof Number n)return excel(n.doubleValue());String text=input.toString().trim();try{double value=Double.parseDouble(text);if(value>=0&&value<=100_000)return excel(value);}catch(Exception ignored){}List<DateTimeFormatter>formats=List.of(DateTimeFormatter.ISO_LOCAL_DATE_TIME,flex("d/M/uuuu"),flex("d-M-uuuu"),flex("uuuu-M-d"),flex("d-MMM-uuuu"));for(DateTimeFormatter f:formats)try{return LocalDateTime.parse(text,f);}catch(Exception ignored){}try{return OffsetDateTime.parse(text).toLocalDateTime();}catch(Exception ignored){return null;}}
 private static DateTimeFormatter flex(String date){return new DateTimeFormatterBuilder().parseCaseInsensitive().appendPattern(date+" H:mm[:ss]").optionalStart().appendFraction(ChronoField.NANO_OF_SECOND,0,9,true).optionalEnd().toFormatter(Locale.UK);}
 private static LocalDateTime excel(double value){return LocalDateTime.of(1899,12,30,0,0).plusSeconds(Math.round(value*86_400));}
 private static Object typed(String value){if(value==null||value.isBlank())return null;try{double d=Double.parseDouble(value.trim());return Double.isFinite(d)?d:null;}catch(Exception e){return value.trim();}}
 private static LocalDate date(String value){try{return value==null||value.isBlank()?null:LocalDate.parse(value);}catch(Exception e){return null;}}
 private static LocalTime time(String value,LocalTime fallback){try{return value==null||value.isBlank()?fallback:LocalTime.parse(value);}catch(Exception e){return fallback;}}
}
