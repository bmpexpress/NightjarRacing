## Nightjar Data Analysis 0.9.4
Java 21 / Spring Boot update for the Nightjar data-analysis site.

### Update contents
- Continuous colour scale bars on Map View, Variable plot and Polar plots.
- Transparent/darker plot presentation aligned with the site theme.
- Port tack is red and starboard tack is green whenever Colour by tack is selected.
- Sidebar toggle is inline with the tab strip and GPS is renamed Map View.
- VMG_PCT maps to Expedition's VMG% channel by default when present.
- Files tab can switch between filtered EventData and TestData tables.
- TestData.csv is loaded automatically from NIGHTJAR_DATA_DIR and can also be uploaded.

Merge this folder over 0.9.3 so unchanged deployment files and Logo.png are retained. Build with `mvn clean test package`.
