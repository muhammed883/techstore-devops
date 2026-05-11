# Jenkins CI/CD Setup

Build and run Jenkins with Docker CLI support:

```powershell
docker build -t techstore-jenkins -f jenkins/Dockerfile .
docker rm -f jenkins
docker run -d `
  -p 8080:8080 `
  -p 50000:50000 `
  -v jenkins_home:/var/jenkins_home `
  -v /var/run/docker.sock:/var/run/docker.sock `
  --network techstore-devops_techstore-net `
  --name jenkins `
  techstore-jenkins
```

Or start it with the project compose stack:

```powershell
docker compose up -d jenkins
```

Get the initial admin password:

```powershell
docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

If this file does not exist, Jenkins has already completed its first setup on the current Docker volume. To start a completely fresh setup, remove the Jenkins volume and recreate the container:

```powershell
docker rm -f jenkins
docker volume rm techstore-devops_jenkins-data
docker compose up -d jenkins
```

Open Jenkins at:

```text
http://localhost:8080
```

Install suggested plugins, then make sure these plugins are available:

- Pipeline
- GitHub Integration
- Docker Pipeline
- SonarQube Scanner
- Slack Notification
- Cobertura
- Blue Ocean

Create the pipeline:

- New Item > Pipeline
- Name: `techstore-pipeline`
- Definition: `Pipeline script from SCM`
- SCM: `Git`
- Repository URL: `https://github.com/muhammed883/techstore-devops`
- Branch Specifier: `*/main`
- Script Path: `Jenkinsfile`
- Save > Build Now

Pipeline stages:

1. Checkout
2. Install Dependencies
3. Unit And Integration Tests
4. Coverage
5. SonarQube Analysis
6. Quality Gate
7. Docker Build
8. Docker Push
9. Deploy
10. Smoke Test
11. UI Tests

After the first build starts, open the pipeline dashboard:

```text
http://localhost:8080/job/techstore-pipeline/
```

Notes:

- `Docker Push` runs only when the `PUSH_IMAGE` parameter is checked.
- `UI Tests` runs only when the `RUN_UI_TESTS` parameter is checked.
- `Quality Gate` runs only when `WAIT_FOR_QUALITY_GATE` is checked and a SonarQube webhook is configured.
- Jenkins runs inside Docker, so the pipeline smoke test uses `http://techstore-app:5000/health`. From your browser or host terminal, use `http://localhost:5000/health`.

## SonarQube Quality Gate

Open SonarQube:

```text
http://localhost:9000
```

Create the project manually:

- Project key: `techstore`
- Display name: `TechStore E-Commerce`
- Analysis method: `Locally`

Create and copy a token from SonarQube. Then configure Jenkins:

- Manage Jenkins > System > SonarQube servers
- Check/Add `Environment variables`
- Name: `SonarQube`
- Server URL: `http://sonarqube:9000`
- Server authentication token: select/create a Secret Text credential with the copied token

Use `http://sonarqube:9000` inside Jenkins because Jenkins runs in the same Docker network as SonarQube. Browser access remains `http://localhost:9000`.

If the build fails with this message:

```text
SonarQube installation defined in this job (SonarQube) does not match any configured installation
```

then the Jenkins global SonarQube server has not been configured yet. Go to:

```text
http://localhost:8080/manage/configure
```

and add the SonarQube server exactly as `Name: SonarQube`. The name is case-sensitive.

For a temporary pipeline-only smoke run, build with parameter `RUN_SONAR=false`. This skips SonarQube analysis while keeping tests, coverage, Docker build, deploy, and smoke test active.

Required Jenkins credentials:

- `docker-hub-creds`: Username/password for Docker Hub, only needed when `PUSH_IMAGE=true`.

Recommended webhook:

```text
http://localhost:8080/github-webhook/
```

For SonarQube Quality Gate callbacks, add this webhook in SonarQube if you enable `WAIT_FOR_QUALITY_GATE`:

```text
http://jenkins:8080/sonarqube-webhook/
```

Grafana: `http://localhost:3000` with `admin / techstore123`.
SonarQube: `http://localhost:9000` with `admin / admin` on first login.
