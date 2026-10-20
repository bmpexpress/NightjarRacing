# Nightjar Data Analysis 0.9.5

Version 0.9.5 reorganises the application into independently maintained HTML page fragments and JavaScript modules. `index.html` is now only the application shell. `js/app.js` loads the fragments in `pages/`, initialises authentication, state and navigation, and delegates each tab to its own module.

## Build

```bash
mvn clean test package
```

The application reads volume data from `NIGHTJAR_DATA_DIR` (default `/Data`), including `logfile.csv`, `EventData.csv`, `TestData.csv` and `EventList.txt`.

Copy the existing `Logo.png`, Dockerfile and Railway configuration into the project if those deployment assets are held outside the source structure.
