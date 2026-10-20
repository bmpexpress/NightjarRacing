package com.nightjar.analysis;

import jakarta.servlet.http.*;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.servlet.mvc.method.annotation.StreamingResponseBody;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.*;

@RestController
@RequestMapping("/api")
public class WebController {
 private final DataStore store; private final String passwordHash;
 public WebController(DataStore store){this.store=store;String hash=System.getenv().getOrDefault("NIGHTJAR_APP_PASSWORD_SHA256","").trim().toLowerCase(Locale.ROOT);String plain=System.getenv().getOrDefault("NIGHTJAR_APP_PASSWORD","");passwordHash=hash.isBlank()?(plain.isBlank()?"":sha256(plain)):hash;}
 record LoginRequest(String password){}
 @GetMapping("/auth") Map<String,Object> auth(HttpSession s){return Map.of("required",!passwordHash.isBlank(),"authenticated",authorised(s));}
 @PostMapping("/login") ResponseEntity<?> login(@RequestBody LoginRequest r,HttpSession s){if(passwordHash.isBlank()||constant(passwordHash,sha256(r.password()==null?"":r.password()))){s.setAttribute("nightjarAuthenticated",true);return ResponseEntity.ok(Map.of("ok",true));}return ResponseEntity.status(401).body(Map.of("error","Incorrect password"));}
 @PostMapping("/logout") void logout(HttpSession s){s.invalidate();}
 @GetMapping("/state") ResponseEntity<?> state(HttpSession s){return authorised(s)?ResponseEntity.ok(store.state()):unauthorised();}
 @PostMapping(value="/upload",consumes=MediaType.MULTIPART_FORM_DATA_VALUE) ResponseEntity<?> upload(HttpSession s,@RequestPart(value="log",required=false)MultipartFile log,@RequestPart(value="polar",required=false)MultipartFile polar,@RequestPart(value="events",required=false)MultipartFile events,@RequestPart(value="eventList",required=false)MultipartFile eventList,@RequestPart(value="sailChart",required=false)MultipartFile sail,@RequestPart(value="debrief",required=false)MultipartFile debrief){if(!authorised(s))return unauthorised();store.upload(log,polar,events,eventList,sail,debrief);return ResponseEntity.ok(store.state());}
 @PostMapping("/settings") ResponseEntity<?> settings(@RequestBody Models.SettingsRequest r,HttpSession s){if(!authorised(s))return unauthorised();store.updateSettings(r);return ResponseEntity.ok(store.state());}
 @PostMapping("/data") ResponseEntity<?> data(@RequestBody Models.FilterRequest r,HttpSession s){return authorised(s)?ResponseEntity.ok(store.filtered(r,false)):unauthorised();}
 @PostMapping("/plot-data") ResponseEntity<?> plotData(@RequestBody Models.FilterRequest r,HttpSession s){return authorised(s)?ResponseEntity.ok(store.filtered(r,true)):unauthorised();}
 @PostMapping(value="/export",produces="text/csv") ResponseEntity<StreamingResponseBody> export(@RequestBody Models.FilterRequest r,HttpSession s){if(!authorised(s))return ResponseEntity.status(401).build();Models.DataResponse data=store.filtered(r,false);StreamingResponseBody body=out->{try(Writer w=new BufferedWriter(new OutputStreamWriter(out,StandardCharsets.UTF_8),1024*1024)){if(data.rows().isEmpty())return;List<String> headers=new ArrayList<>(data.rows().get(0).keySet());writeCsv(w,headers);for(Map<String,Object> row:data.rows()){List<String> values=headers.stream().map(h->Objects.toString(row.get(h),"")).toList();writeCsv(w,values);}}};return ResponseEntity.ok().header(HttpHeaders.CONTENT_DISPOSITION,"attachment; filename=nightjar_filtered_log_0.9.2.csv").body(body);}
 @GetMapping("/session") ResponseEntity<?> session(HttpSession s){if(!authorised(s))return unauthorised();Map<String,Object> state=store.state();Map<String,Object> out=new LinkedHashMap<>();out.put("version",NightjarApplication.VERSION);out.put("createdUtc",Instant.now());out.put("rowCount",state.get("rowCount"));out.put("mapping",state.get("mapping"));out.put("includedVariables",state.get("includedVariables"));out.put("plotDownsamplingEnabled",state.get("plotDownsamplingEnabled"));out.put("maxPlotPoints",state.get("maxPlotPoints"));return ResponseEntity.ok().header(HttpHeaders.CONTENT_DISPOSITION,"attachment; filename=nightjar_session_0.9.2.json").body(out);}
 private static void writeCsv(Writer w,List<String> values)throws IOException{for(int i=0;i<values.size();i++){if(i>0)w.write(',');w.write('"');w.write(values.get(i).replace("\"","\"\""));w.write('"');}w.write('\n');}
 private boolean authorised(HttpSession s){return passwordHash.isBlank()||Boolean.TRUE.equals(s.getAttribute("nightjarAuthenticated"));}
 private static ResponseEntity<Map<String,String>> unauthorised(){return ResponseEntity.status(401).body(Map.of("error","Sign in required"));}
 private static boolean constant(String a,String b){return MessageDigest.isEqual(a.getBytes(StandardCharsets.UTF_8),b.getBytes(StandardCharsets.UTF_8));}
 private static String sha256(String v){try{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(v.getBytes(StandardCharsets.UTF_8)));}catch(Exception e){throw new IllegalStateException(e);}}
}
