# Task API

A RESTful Task Management API built with **FastAPI** and **PostgreSQL**, running inside **Docker**. This project provides CRUD operations for tasks while demonstrating persistent database storage, environment configuration, and containerized deployment.

## Features

- Create, Read, Update, and Delete tasks
- PostgreSQL database for persistent storage
- Dockerized application and database
- Environment variables using `.env`
- Automatic table creation on startup
- Sample data inserted on the first run
- Interactive API documentation with Swagger UI

---

## Tech Stack

- Python 3.12
- FastAPI
- PostgreSQL
- Psycopg
- Docker & Docker Compose
- Pydantic
- Python Dotenv

---

## Project Structure

```
.
├── main.py
├── database.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/Fatima-26-23/task-api.git
cd task-api
```

### 2. Create a `.env` file

Copy `.env.example` and add your PostgreSQL configuration.

Example:

```env
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DB=taskdb
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```

---

## Run the Project

Build and start the application and PostgreSQL:

```bash
docker compose up --build
```

After the containers start:

- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs

---

## API Endpoints

| Method | Endpoint | Description |
|---------|----------|-------------|
| GET | `/` | API information |
| GET | `/health` | Health check |
| GET | `/tasks` | Get all tasks |
| GET | `/tasks/{id}` | Get task by ID |
| POST | `/tasks` | Create a task |
| PUT | `/tasks/{id}` | Update a task |
| DELETE | `/tasks/{id}` | Delete a task |

---

## Database

The application automatically:

- Connects to PostgreSQL
- Creates the `tasks` table if it does not exist
- Inserts sample tasks only when the table is empty

Task table:

| Column | Type |
|---------|------|
| id | SERIAL PRIMARY KEY |
| title | TEXT |
| done | BOOLEAN |

---

## Persistence Verification

Persistence was verified by:

1. Starting the application using Docker Compose.
2. Creating new tasks through the API.
3. Stopping both containers using:

```bash
docker compose down
```

4. Restarting the application using:

```bash
docker compose up
```

5. Confirming that all previously created tasks were still present.

---

## Environment Variables

Create a `.env` file using `.env.example`.

Required variables:

```env
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DB=taskdb
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```

---

## Notes

- `.env` is excluded from Git using `.gitignore`.
- PostgreSQL runs inside a Docker container.
- Docker Compose starts both the FastAPI application and PostgreSQL with a single command.

---

## Author

**Fatima Qadeer**

Computer Science Student | FAST-NUCES