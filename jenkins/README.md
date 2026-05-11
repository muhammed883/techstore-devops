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

Get the initial admin password:

```powershell
docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

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
- Name: `SonarQube`
- Server URL: `http://sonarqube:9000`
- Server authentication token: select/create a Secret Text credential with the copied token

Use `http://sonarqube:9000` inside Jenkins because Jenkins runs in the same Docker network as SonarQube. Browser access remains `http://localhost:9000`.

Required Jenkins credentials:

- `docker-hub-creds`: Username/password for Docker Hub, only needed when `PUSH_IMAGE=true`.

Recommended webhook:

```text
http://localhost:8080/github-webhook/
```

Grafana: `http://localhost:3000` with `admin / techstore123`.
SonarQube: `http://localhost:9000` with `admin / admin` on first login.
