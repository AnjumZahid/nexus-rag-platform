# MySQL Database Setup with Docker Desktop and Docker Compose

This guide explains how to run MySQL for the RAG application using Docker Desktop and Docker Compose.

The setup provides:

- MySQL 8.4
- A dedicated `rag_app` database
- A dedicated `rag_user` application user
- Persistent database storage using a Docker volume
- A health check
- Local access through port `3306`
- A reproducible setup for other developers

---

## 1. Prerequisites

Install and start:

- Docker Desktop
- Python project environment
- `uv`

Open PowerShell in the project root:

```powershell
cd C:\Users\Admin\Downloads\rag_app
```

Verify Docker:

```powershell
docker version
docker compose version
```

Docker Desktop must show that the Docker engine is running.

---

## 2. Ensure Port 3306 Is Available

Check whether another MySQL server or Docker container is already using port `3306`:

```powershell
netstat -ano | findstr :3306
```

If a Windows MySQL service is running, stop it before starting the Docker database.

Check for an existing container:

```powershell
docker ps -a --filter "name=ragdb-mysql"
```

Remove an old container only when it is no longer needed:

```powershell
docker rm -f ragdb-mysql
```

Do not delete an existing Docker volume if it contains important data.

---

## 3. Create `compose.yml`

Create this file in the project root:

```text
compose.yml
```

Add:

```yaml
services:
  mysql:
    image: mysql:8.4
    container_name: ragdb-mysql
    restart: unless-stopped

    env_file:
      - .env.docker

    ports:
      - "127.0.0.1:3306:3306"

    volumes:
      - rag_mysql_data:/var/lib/mysql

    command:
      - --character-set-server=utf8mb4
      - --collation-server=utf8mb4_unicode_ci

    healthcheck:
      test:
        [
          "CMD-SHELL",
          "mysqladmin ping -h 127.0.0.1 -u root -p$$MYSQL_ROOT_PASSWORD --silent",
        ]
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 30s

volumes:
  rag_mysql_data:
    name: rag_mysql_data
```

### What this configuration creates

```text
Docker image: mysql:8.4
Container:    ragdb-mysql
Database:     rag_app
Volume:       rag_mysql_data
Host port:    3306
```

The MySQL server runs inside the `ragdb-mysql` container.

The actual database files are stored persistently in the Docker volume:

```text
rag_mysql_data
```

The volume is mounted inside the container at:

```text
/var/lib/mysql
```

Deleting and recreating the container does not delete the database as long as the volume remains.

---

## 4. Create `.env.docker`

Create this file in the project root:

```text
.env.docker
```

Add:

```env
MYSQL_ROOT_PASSWORD=replace_with_a_strong_root_password

MYSQL_DATABASE=rag_app

MYSQL_USER=rag_user
MYSQL_PASSWORD=replace_with_a_strong_application_password
```

Example development values:

```env
MYSQL_ROOT_PASSWORD=RootPassword_2026_Local_8x
MYSQL_DATABASE=rag_app
MYSQL_USER=rag_user
MYSQL_PASSWORD=RagUserPassword_2026_7x
```

Use your own strong passwords.

For easier use inside `DATABASE_URL`, avoid characters such as:

```text
@ : / # %
```

These characters require URL encoding.

---

## 5. Protect Secret Files

Ensure `.gitignore` contains:

```gitignore
.env
.env.docker

data/chroma/
data/chroma_test/
```

Never commit `.env` or `.env.docker` to GitHub.

For a public project, provide an example file such as:

```text
.env.docker.example
```

with placeholder values instead of real passwords.

---

## 6. Start the MySQL Container

Run:

```powershell
docker compose up -d
```

Docker Compose will:

```text
Download mysql:8.4 if it is missing
→ create the ragdb-mysql container
→ create the rag_mysql_data volume
→ initialize the rag_app database
→ create the rag_user account
→ start the MySQL server
```

Check status:

```powershell
docker compose ps
```

Check logs:

```powershell
docker compose logs --tail 100 mysql
```

Wait until the status shows:

```text
healthy
```

You can also follow logs continuously:

```powershell
docker compose logs -f mysql
```

Press `Ctrl + C` to stop viewing logs. This does not stop the container.

---

## 7. Verify the Persistent Volume

List the volume:

```powershell
docker volume ls | findstr rag_mysql_data
```

Inspect it:

```powershell
docker volume inspect rag_mysql_data
```

The volume stores MySQL database files on the local machine through Docker-managed storage.

---

## 8. Test MySQL Inside the Container

Open the MySQL command line inside the running container:

```powershell
docker exec -it ragdb-mysql mysql -u rag_user -p
```

Enter the password configured in:

```text
MYSQL_PASSWORD
```

Then run:

```sql
SHOW DATABASES;

USE rag_app;

SHOW TABLES;

EXIT;
```

At the beginning, `rag_app` may contain no application tables. Tables will be created later through database models and migrations.

---

## 9. Configure the Python Application

The Python application currently runs directly on Windows, while MySQL runs inside Docker.

Add this to the application's `.env` file:

```env
DATABASE_URL=mysql+asyncmy://rag_user:your_application_password@127.0.0.1:3306/rag_app
```

Example:

```env
DATABASE_URL=mysql+asyncmy://rag_user:RagUserPassword_2026_7x@127.0.0.1:3306/rag_app
```

Install the required packages if they are not already installed:

```powershell
uv add "sqlalchemy[asyncio]" asyncmy cryptography
```

Test the connection:

```powershell
uv run python -m tests.test_database_connection
```

Expected output:

```text
mysql_connection_check_completed
MySQL connection test passed successfully.
```

---

## 10. View the Container in Docker Desktop

Open Docker Desktop.

Under **Containers**, you should see:

```text
ragdb-mysql
```

You can inspect:

- Container status
- Logs
- Port mapping
- CPU usage
- Memory usage
- Environment variables

Under **Volumes**, you should see:

```text
rag_mysql_data
```

---

## 11. Useful Docker Compose Commands

### Start the database

```powershell
docker compose up -d
```

### View container status

```powershell
docker compose ps
```

### View logs

```powershell
docker compose logs --tail 100 mysql
```

### Follow logs

```powershell
docker compose logs -f mysql
```

### Stop MySQL without removing the container

```powershell
docker compose stop
```

### Start an existing stopped container

```powershell
docker compose start
```

### Stop and remove the container while keeping database data

```powershell
docker compose down
```

The `rag_mysql_data` volume remains.

Start again with the same database:

```powershell
docker compose up -d
```

### Delete the container and all database data

```powershell
docker compose down -v
```

> Warning: `-v` deletes the `rag_mysql_data` volume and permanently removes the database data.

---

## 12. Important Initialization Rule

The official MySQL Docker image uses these variables only when the MySQL data directory is empty:

```text
MYSQL_ROOT_PASSWORD
MYSQL_DATABASE
MYSQL_USER
MYSQL_PASSWORD
```

After the `rag_mysql_data` volume has been initialized, changing `.env.docker` does not automatically change the existing MySQL user or password.

To change an existing password, connect to MySQL and use SQL commands such as:

```sql
ALTER USER 'rag_user'@'%'
IDENTIFIED BY 'new_password';
```

Then update the application's `.env` file with the same new password.

To completely initialize MySQL again from scratch:

```powershell
docker compose down -v
docker compose up -d
```

> This permanently deletes all existing database data.

---

## 13. Local Development vs Fully Dockerized Deployment

Currently:

```text
Python/FastAPI application → runs on Windows
MySQL                    → runs in Docker
```

Therefore the database host is:

```text
127.0.0.1
```

Current connection:

```env
DATABASE_URL=mysql+asyncmy://rag_user:password@127.0.0.1:3306/rag_app
```

Later, if the FastAPI backend is also added to the same Docker Compose network, it should connect using the Compose service name:

```env
DATABASE_URL=mysql+asyncmy://rag_user:password@mysql:3306/rag_app
```

Inside Docker Compose, `mysql` is the service name and acts as the internal hostname.

---

## 14. Recommended Production Approach

For local production-grade development:

```text
Docker Desktop + Docker Compose + persistent named volume
```

For real production deployment, a managed MySQL service is usually preferred because it can provide:

- Automated backups
- Monitoring
- High availability
- Encryption
- Easier scaling
- Managed updates

If MySQL is deployed in Docker on a VPS, also configure:

- Automated database backups
- Private networking
- Firewall restrictions
- Strong secrets
- Monitoring
- Disk-space alerts
- Restore testing
- Container restart policy
- Volume backup strategy

Do not publicly expose MySQL port `3306` in production unless strictly required and protected.

---

## 15. Architecture Summary

```text
Docker Hub
    ↓
downloads mysql:8.4 image
    ↓
Docker Compose creates ragdb-mysql
    ↓
MySQL Server runs inside the container
    ↓
rag_app database is created
    ↓
database files are stored in rag_mysql_data
    ↓
Python application connects through 127.0.0.1:3306
```

This setup gives the RAG application a repeatable and persistent MySQL development environment.
