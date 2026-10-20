# Nightjar Data Analysis 0.9.5.1

Corrective release for 0.9.5. The modular pages and JavaScript structure is retained. Volume loading is moved out of the WebController constructor and restored to a dedicated DataStore service using buffered, sequential readers. The large logfile is never loaded with Files.readAllBytes. EventData and TestData are also parsed through buffered readers and capped at 20,000 display rows.

Build: `mvn clean package`
