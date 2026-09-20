Nightjar Data Analysis 0.9.1 patch

Overwrite these files in the existing 0.9.1 project:
- src/main/java/com/nightjar/analysis/DataStore.java
- src/main/resources/static/app.js
- src/main/resources/static/index.html

Fixes:
- EventData dates such as 26-Mar-2026 20:34:20 are now parsed using a case-insensitive d-MMM-uuuu format.
- Adds a Sail selection tab and renders closed, filled Expedition sail boundaries using the colour, opacity and line width parsed from SailChart.xml.
