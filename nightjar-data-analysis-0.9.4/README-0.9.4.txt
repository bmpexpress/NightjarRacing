Nightjar Data Analysis 0.9.4 overwrite files

Copy the contents of this folder over the root of the existing 0.9.3 project and allow matching files to be replaced.
The package contains complete replacement files, plus the new AuxiliaryDataStore.java and v094-enhancements.js files.
Keep all existing files not included here, including DataStore.java, Models.java, app.js, Logo.png, Dockerfile and railway.toml.

TestData is read automatically from NIGHTJAR_DATA_DIR/TestData.csv. EventData continues to use EventData.csv.
Build command: mvn clean test package
