FROM maven:3.9.11-eclipse-temurin-21 AS build
WORKDIR /workspace
COPY pom.xml .
RUN mvn -B -q dependency:go-offline
COPY src src
RUN mvn -B -q test package
FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build /workspace/target/nightjar-data-analysis-0.9.0.jar app.jar
EXPOSE 8080
ENV JAVA_TOOL_OPTIONS="-Xms256m -Xmx4096m -Xss512k -XX:+UseG1GC -XX:MaxDirectMemorySize=256m -XX:MaxMetaspaceSize=256m -XX:+ExitOnOutOfMemoryError"
ENV NIGHTJAR_LOAD_HEAP_LIMIT_MB="3200"
ENTRYPOINT ["java","-jar","/app/app.jar"]
