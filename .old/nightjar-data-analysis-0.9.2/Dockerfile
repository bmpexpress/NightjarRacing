FROM maven:3.9.11-eclipse-temurin-21 AS build
WORKDIR /workspace
COPY pom.xml .
RUN mvn -B -q dependency:go-offline
COPY src src
RUN mvn -B -q test package && cp target/nightjar-data-analysis-*.jar target/app.jar

FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build /workspace/target/app.jar app.jar
ENV JAVA_TOOL_OPTIONS="-Xms256m -Xmx4096m -Xss512k -XX:+UseG1GC -XX:MaxDirectMemorySize=256m -XX:MaxMetaspaceSize=256m -XX:+ExitOnOutOfMemoryError"
EXPOSE 8080
ENTRYPOINT ["java","-jar","/app/app.jar"]
