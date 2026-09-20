package com.nightjar.analysis;

import jakarta.servlet.http.HttpSession;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.*;

@RestController
@RequestMapping("/api")
public class WebController {
    private final DataStore store;
    private final String passwordHash;
    public WebController(DataStore store) {
        this.store = store;
        String configuredHash = System.getenv().getOrDefault("NIGHTJAR_APP_PASSWORD_SHA256", "").trim().toLowerCase(Locale.ROOT);
        String configuredPlain = System.getenv().getOrDefault("NIGHTJAR_APP_PASSWORD", "");
        this.passwordHash = configuredHash.isBlank() ? (configuredPlain.isBlank() ? "" : sha256(configuredPlain)) : configuredHash;
    }

    record LoginRequest(String password) {}

    @GetMapping("/auth") public Map<String,Object> auth(HttpSession session) {
        return Map.of("required", !passwordHash.isBlank(), "authenticated", authorised(session));
    }
    @PostMapping("/login") public ResponseEntity<?> login(@RequestBody LoginRequest request, HttpSession session) {
        if (passwordHash.isBlank() || constantEquals(passwordHash, sha256(request.password() == null ? "" : request.password()))) {
            session.setAttribute("nightjarAuthenticated", true); return ResponseEntity.ok(Map.of("ok",true));
        }
        return ResponseEntity.status(401).body(Map.of("error","Incorrect password"));
    }
    @PostMapping("/logout") public void logout(HttpSession session) { session.invalidate(); }

    @GetMapping("/state") public ResponseEntity<?> state(HttpSession session) {
        if (!authorised(session)) return unauthorised(); return ResponseEntity.ok(store.state());
    }

    @PostMapping(value="/upload", consumes=MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<?> upload(HttpSession session,
        @RequestPart(value="log",required=false) MultipartFile log,
        @RequestPart(value="polar",required=false) MultipartFile polar,
        @RequestPart(value="events",required=false) MultipartFile events,
        @RequestPart(value="eventList",required=false) MultipartFile eventList,
        @RequestPart(value="sailChart",required=false) MultipartFile sailChart,
        @RequestPart(value="debrief",required=false) MultipartFile debrief) {
        if (!authorised(session)) return unauthorised();
        try { store.upload(log,polar,events,eventList,sailChart,debrief); return ResponseEntity.ok(store.state()); }
        catch(Exception e) { return ResponseEntity.badRequest().body(Map.of("error",e.getMessage()==null?e.getClass().getSimpleName():e.getMessage())); }
    }

    @PostMapping("/settings") public ResponseEntity<?> settings(@RequestBody Models.SettingsRequest request, HttpSession session) {
        if (!authorised(session)) return unauthorised(); store.updateSettings(request); return ResponseEntity.ok(store.state());
    }
    @PostMapping("/data") public ResponseEntity<?> data(@RequestBody Models.FilterRequest request, HttpSession session) {
        if (!authorised(session)) return unauthorised(); return ResponseEntity.ok(store.filtered(request));
    }
    @PostMapping(value="/export", produces="text/csv") public ResponseEntity<?> export(@RequestBody Models.FilterRequest request, HttpSession session) {
        if (!authorised(session)) return unauthorised();
        Models.DataResponse data=store.filtered(request); StringBuilder csv=new StringBuilder();
        if(!data.rows().isEmpty()){
            List<String> headers=new ArrayList<>(data.rows().get(0).keySet()); csv.append(headers.stream().map(WebController::quote).reduce((a,b)->a+","+b).orElse("")).append('\n');
            for(Map<String,Object> row:data.rows()) csv.append(headers.stream().map(h->quote(Objects.toString(row.get(h),""))).reduce((a,b)->a+","+b).orElse("")).append('\n');
        }
        return ResponseEntity.ok().header(HttpHeaders.CONTENT_DISPOSITION,"attachment; filename=nightjar_filtered_log_0.9.0.csv").body(csv.toString());
    }
    @GetMapping(value="/session", produces=MediaType.APPLICATION_JSON_VALUE) public ResponseEntity<?> session(HttpSession session) {
        if (!authorised(session)) return unauthorised();
        Map<String,Object> state=store.state();
        return ResponseEntity.ok().header(HttpHeaders.CONTENT_DISPOSITION,"attachment; filename=nightjar_session_0.9.0.json")
            .body(Map.of("version",NightjarApplication.VERSION,"createdUtc",Instant.now(),"rowCount",state.get("rowCount"),"mapping",state.get("mapping"),"includedVariables",state.get("includedVariables")));
    }

    private boolean authorised(HttpSession session){return passwordHash.isBlank() || Boolean.TRUE.equals(session.getAttribute("nightjarAuthenticated"));}
    private static ResponseEntity<Map<String,String>> unauthorised(){return ResponseEntity.status(401).body(Map.of("error","Sign in required"));}
    private static boolean constantEquals(String a,String b){return b!=null && MessageDigest.isEqual(a.getBytes(StandardCharsets.UTF_8),b.getBytes(StandardCharsets.UTF_8));}
    private static String sha256(String value){
        try { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8))); }
        catch (Exception ex) { throw new IllegalStateException("SHA-256 is unavailable", ex); }
    }
    private static String quote(String s) {
		String x = s.replace("\"", "\"\"");
		return "\"" + x + "\"";
	}
}
