# 0.9.5.1
- Removed all volume loading from the WebController constructor.
- Reinstated a dedicated DataStore service with PostConstruct startup loading.
- Replaced Files.readAllBytes for the logfile with buffered sequential parsing.
- Added a heap reserve check and partial-load warning.
- Kept the 0.9.5 modular HTML and JavaScript structure.
- Retained EventData and TestData row counts and table API.
