# Nightjar Data Analysis 0.9.2

GitHub-ready Java 21 / Spring Boot application for analysing Expedition sailing data.

## 0.9.2 highlights

- Uses the supplied Nightjar `Logo.png` on the login page, application header and browser icon.
- Restores the blue interface, with orange reserved for selection and highlights.
- Adds Inshore/Offshore event filtering and places event controls above file inputs.
- Adds colour by tack and colour by event to Polar, GPS and Variable plots.
- Adds configurable time averaging and maximum within-bin variation.
- Adds half-polar, full-polar and Cartesian polar views.
- GPS tooltips include TWS, TWA, BSP, Heel and the selected plotted variable when mapped.
- Retains memory-safe plot downsampling and active-tab plot rendering.

## Build

```bash
mvn clean test package
```

## Railway

The Dockerfile stages the versioned Maven output as `app.jar`, so later version changes do not require a hard-coded JAR filename update.
