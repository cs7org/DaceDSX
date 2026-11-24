# Quickstart

This guide is intended for **Ubuntu 22.04** (Jammy Jellyfish) or [**WSL 2**](https://learn.microsoft.com/en-us/windows/wsl/install).

## Prerequisites

- [**JDK 11**](https://jdk.java.net/archive/)
   ``````bash
   JDK_URL="https://download.java.net/java/GA/jdk11/9/GPL/openjdk-11.0.2_linux-x64_bin.tar.gz"

   wget -o ./openjdk.tar.gz "$JDK_URL"
   JDK_DIR=$(tar -tzf openjdk.tar.gz | head -1 | cut -d/ -f1)
   # Install for all users
   sudo tar -xzf openjdk.tar.gz -C /usr/lib/jvm && rm ./openjdk.tar.gz

   echo 'export JAVA_HOME="/usr/lib/jvm/'"$JDK_DIR"'"' >> ~/.bashrc
   echo 'export PATH="$JAVA_HOME/bin:$PATH"' >> ~/.bashrc
   ``````
- [**Maven**](https://maven.apache.org/install.html)
   ``````bash
   sudo apt install --yes maven
   ``````
- **Docker**
   - Either install Docker Engine or Docker Desktop
      - **Docker Desktop**
         - Refer to the [install guide](https://docs.docker.com/get-started/get-docker/)
         - *Windows*: Enable **"Use the WSL 2 based engine"** in Docker settings → General.
         - *Linux*: Enable the **docker‑compose** CLI alias in Docker settings → General.
      - **Docker Engine**
         - Refer to the [install guide](https://docs.docker.com/engine/install/)
         > [!NOTE]
         > In WSL, if Docker installation fails, execute
         >  ```bash
         >  dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
         >  wsl --update
         >  ```
   
- **Confluent Platform** via Docker Compose
   ```bash
   mkdir confluence
   wget -O ./confluence/docker-compose.yml https://raw.githubusercontent.com/confluentinc/cp-all-in-one/refs/heads/7.5.2-post/cp-all-in-one/docker-compose.yml
   ```

## Compiling DaceDSX

1. **Clone the repository** (or download the source).
2. Build the core components:
   ```bash
   # from repository root
   cd ./JavaBaseWrapper
   mvn install
   cd ../SimService
   mvn install
   ```
   > [!NOTE]
   > If the build fails, force TLS 1.2 (required for some JDK 11 setups):
   > ```bash
   > mvn install -Dhttps.protocols=TLSv1.2
   > ```

3. Build any optional wrappers (e.g., SumoWrapper) as needed.

## Running a Scenario

1. **Prepare configuration** - place `config.properties` next to the JARs and move it into the `target` directory:
   ```bash
   # from repository root
   # replaces all .properties.template in this repo to .properties, replacing <repo-dir> with local absolute path
   find . -type f -name '*.properties.template' -exec bash -c 'sed "s|<repo-dir>|$1|g" "$2" > "${2%.template}"' _ "$PWD" {} \;
   mv ./SimService/config.properties ./SimService/target/config.properties
   ```
2. **Start Kafka via Docker**:
   ```bash
   # from confluence folder
   docker-compose up -d
   docker-compose ps
   ```
3. **Run the simulation service**:
   ```bash
   # Use sudo only if your Docker/Kafka setup requires it
   java -jar ./SimService/target/SimService-0.1-jar-with-dependencies.jar
   ```
4. **Send a scenario**:
   ```bash
   java -jar ./SimService/target/SendScenarioObject.jar ./_data/scenarios/scenario.json
   ```
