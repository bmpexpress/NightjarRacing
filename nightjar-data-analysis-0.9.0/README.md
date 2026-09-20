# Nightjar Data Analysis 0.9.0

A Java/Spring Boot rebuild of the Nightjar sailing-data analysis web app. The browser UI is normal HTML/CSS/JavaScript; Java provides file parsing, filtering, UTC/BST handling, settings, downloads and data APIs.

## Implemented in 0.9.0

- Version uplift to **0.9.0** throughout the application and downloads.
- Replaced Streamlit/Python deployment with **Java 21 + Spring Boot** and a standard static web front end.
- Treats Expedition GUN timestamps as **UTC** and converts them with `Europe/London` zone rules before applying the GUN-minus-five-minutes crop. This applies BST (+01:00) only when in force and GMT (+00:00) otherwise.
- Nightjar navy/orange design applied consistently to controls, panels, charts and states.
- Persistent orange divider under the top analysis tabs.
- Settings tab lists every channel. Unticked channels are removed from API responses, calculations, selectors, tables and charts.
- Variable plot supports **Time** on either Cartesian axis. Selecting Time while Polar is selected automatically uses Cartesian mode.
- Variation-filter defaults changed from 99 to **1**.
- Times are rounded to the nearest second in charts, GPS hover text, tables and summaries.
- Removed deterministic downsampling, maximum-point limits, DataFrame memory budgets and download-size limits. The full filtered selection is returned and plotted.
- Standard and sparse Expedition logs, polar files, event files, event lists, sail-chart XML and text/DOCX debrief notes are supported.
- Full-resolution CSV and JSON session downloads.
- Optional startup loading from `/Data` (or `NIGHTJAR_DATA_DIR`) using the previous filenames.

## Run locally

Requirements: Java 21 and Maven 3.9+.

```bash
mvn spring-boot:run
```

Open `http://localhost:8080`.

Optional password:

```bash
export NIGHTJAR_APP_PASSWORD='choose-a-strong-password'
mvn spring-boot:run
```

Without `NIGHTJAR_APP_PASSWORD`, the app opens without a sign-in gate.

## Build

```bash
mvn clean test package
java -jar target/nightjar-data-analysis-0.9.0.jar
```

## Docker / Railway

The included `Dockerfile` uses a Maven build stage and Java 21 runtime. It honours Railway's `PORT` environment variable. Deploy the repository as a Dockerfile service and optionally attach a volume mounted at `/Data`.

Recommended variables:

- `NIGHTJAR_APP_PASSWORD_SHA256`: recommended SHA-256 password digest.
- `NIGHTJAR_APP_PASSWORD`: optional plain application password when a digest is not supplied.
- `NIGHTJAR_DATA_DIR`: optional default-data path; defaults to `/Data`.
- `JAVA_OPTS`: JVM settings such as `-Xms512m -Xmx4g -XX:+UseG1GC`.

No application-level memory ceiling is imposed. Set the deployment JVM heap to fit the largest complete log plus browser/API serialisation overhead.

## Time-zone assumption

The uploaded log timestamps are treated as UK local wall-clock times. Expedition event/GUN timestamps are treated as UTC. Java's IANA `Europe/London` rules produce the correct BST/GMT offset for the event date, including transition dates. The included unit tests check summer and winter behaviour.

## Project structure

- `src/main/java/.../DataStore.java` — parsers, derived VMG/VMG%, filters and BST handling.
- `src/main/java/.../WebController.java` — upload, settings, data, export and session APIs.
- `src/main/resources/static/index.html` — seven-page web interface.
- `src/main/resources/static/app.js` — full-resolution plotting and UI calculations.
- `src/main/resources/static/styles.css` — Nightjar styling.
- `src/test/.../DataStoreTimeTest.java` — BST/GMT and timestamp-rounding tests.

## Operational note

Removing downsampling means very large selections are intentionally sent to the browser in full. This meets the requested behaviour but browser rendering and JSON transfer can become the next bottleneck even when server memory is ample. Use event/date filtering where interactive response matters; exports remain full resolution.
