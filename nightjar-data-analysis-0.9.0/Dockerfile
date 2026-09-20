FROM maven:3.9.11-eclipse-temurin-21 AS build
WORKDIR /workspace
COPY pom.xml .
RUN mvn -B -q dependency:go-offline
COPY src src
RUN mvn -B -q package -DskipTests

FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build /workspace/target/nightjar-data-analysis-0.9.0.jar app.jar
EXPOSE 8080
ENV JAVA_OPTS="-XX:+UseG1GC"
ENTRYPOINT ["sh","-c","java $JAVA_OPTS -jar /app/app.jar"]
