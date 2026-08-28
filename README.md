# Enterprise Task Management API

A production-oriented REST API for managing users, projects, and tasks, built with Flask and structured around clean, testable, service-oriented layers. This project demonstrates backend engineering practices — application factory pattern, layered architecture, centralized error handling, and consistent API response contracts — intended as a portfolio-quality reference implementation.

## Overview

The API is being built incrementally, milestone by milestone. This initial milestone establishes the production-oriented application architecture: configuration management, database models, error handling, a consistent response envelope, and a health check endpoint. Authentication and full CRUD functionality for users, projects, and tasks are implemented in subsequent milestones.

## Tech Stack

- **Python 3.11+**
- **Flask** — web framework
- **Flask-SQLAlchemy** — ORM
- **Flask-Migrate** — database migrations (Alembic)
- **Flask-JWT-Extended** — JWT authentication (extension wired up; endpoints coming in the next milestone)
- **Marshmallow** — request/response validation (schemas coming with their respective endpoints)
- **pytest** — testing
- **SQLite** — local development database
- **PostgreSQL** — target production database (via `DATABASE_URL`)
- **python-dotenv** — environment variable loading
- **Gunicorn** — production WSGI server

## Architecture

The application follows a layered structure:

- **Routes** — Flask blueprints define HTTP endpoints and delegate to services.
- **Services** — business logic, independent of the HTTP layer.
- **Schemas** — Marshmallow schemas validate and serialize request/response data.
- **Models** — SQLAlchemy models define the persistence layer.
- **Extensions** — third-party Flask extensions (SQLAlchemy, Migrate, JWT) are initialized once and shared via an application factory.
- **Utils** — cross-cutting concerns: standardized response formatting and centralized error handling.

All routes are created via `create_app()` in [app/\_\_init\_\_.py](app/__init__.py), which loads configuration, initializes extensions, and registers blueprints. This keeps the app instantiable for both the dev server and the test suite without global state.

## Project Structure

```
app/
├── config/         # Environment-based configuration
├── extensions/     # SQLAlchemy, Migrate, JWT instances
├── models/         # User, Project, Task ORM models
├── routes/         # Flask blueprints (health implemented; auth/users/projects/tasks scaffolded)
├── schemas/        # Marshmallow schemas (added alongside their endpoints)
├── services/       # Business logic (added alongside their endpoints)
└── utils/          # Response helpers and error handlers

tests/              # pytest test suite
migrations/         # Alembic migration scripts
```

## Current Features

- Flask application factory with environment-based configuration (development, testing, production)
- SQLAlchemy models for `User`, `Project`, and `Task` with relationships, foreign keys, indexes, and check constraints
- Database migrations via Flask-Migrate
- Versioned API under `/api/v1`
- `GET /api/v1/health` health check endpoint
- User registration (`POST /api/v1/auth/register`) with Marshmallow-validated input, normalized email, unique-email enforcement, and secure password hashing (never returns password or password hash)
- Login (`POST /api/v1/auth/login`) that verifies credentials and issues a Flask-JWT-Extended access token; unknown emails and incorrect passwords return an identical generic error so account existence is never revealed
- Current user lookup (`GET /api/v1/users/me`), protected by JWT bearer authentication
- Consistent JSON success/error response envelope for every HTTP error (400, 404, 405, 500, etc.), not just the happy path
- Centralized error handling: all Werkzeug HTTP exceptions return the standard JSON envelope, and unexpected server errors return a generic 500 with no internal stack trace exposed
- JWT error handling (missing/invalid/expired tokens) also returns the standard JSON envelope instead of Flask-JWT-Extended's default format
- Fail-fast production configuration: `SECRET_KEY`, `JWT_SECRET_KEY`, and `DATABASE_URL` are required (no insecure fallback values) when `FLASK_ENV=production`

## Planned Features

- User registration, login, and JWT-based authentication
- Full CRUD endpoints for users, projects, and tasks
- Request/response validation via Marshmallow schemas
- Role-based access control
- API documentation

## Local Development

```bash
# Clone the repository
git clone https://github.com/Nishar0812/enterprise-task-management-api.git
cd enterprise-task-management-api

# Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env

# Apply database migrations
flask db upgrade

# Run the development server
python run.py
```

The API will be available at `http://127.0.0.1:5000/api/v1`.

## Environment Variables

Documented in [.env.example](.env.example):

| Variable         | Description                                      | Required |
|------------------|---------------------------------------------------|----------|
| `FLASK_ENV`      | `development`, `testing`, or `production`          | No (defaults to `development`) |
| `SECRET_KEY`     | Flask session signing secret                       | Yes, in production (no fallback) |
| `JWT_SECRET_KEY` | JWT signing secret                                 | Yes, in production (no fallback) |
| `DATABASE_URL`   | SQLAlchemy database URI (SQLite locally, PostgreSQL in production) | Yes, in production (no fallback) |

No secrets are committed to this repository. Development and testing use safe local defaults (SQLite, non-secret placeholder keys). When `FLASK_ENV=production`, the app fails fast at startup with a `RuntimeError` if `SECRET_KEY`, `JWT_SECRET_KEY`, or `DATABASE_URL` are not set — it will never silently fall back to a development default.

## Running Tests

```bash
pytest
```

## API

| Method | Endpoint                | Auth required | Description                     |
|--------|--------------------------|:-------------:|----------------------------------|
| GET    | `/api/v1/health`         | No            | Returns service health status    |
| POST   | `/api/v1/auth/register`  | No            | Registers a new user (role defaults to `member`) |
| POST   | `/api/v1/auth/login`     | No            | Verifies credentials and issues a JWT access token |
| GET    | `/api/v1/users/me`       | Yes (Bearer JWT) | Returns the authenticated user's profile |

**Response format (success):**

```json
{
  "success": true,
  "message": "Service is healthy",
  "data": { "service": "enterprise-task-management-api" },
  "error": null
}
```

**Response format (error):**

```json
{
  "success": false,
  "message": "Resource not found",
  "data": null,
  "error": { "code": "NOT_FOUND" }
}
```

### POST /api/v1/auth/register

Request:

```json
{
  "name": "Nishar",
  "email": "nishar@example.com",
  "password": "StrongPassword123!"
}
```

- `name` and `email` are required; `email` must be a valid address and is normalized (trimmed, lowercased) before storage and uniqueness checks.
- `password` is required with a minimum length of 8 characters, and is only ever stored as a secure hash.
- Every new user is created with `role: "member"`.

Success (`201`):

```json
{
  "success": true,
  "message": "User registered successfully",
  "data": { "id": 1, "name": "Nishar", "email": "nishar@example.com", "role": "member" },
  "error": null
}
```

A duplicate email returns `409` with `error.code = "EMAIL_ALREADY_EXISTS"`. Invalid input returns `400` with `error.code = "VALIDATION_ERROR"` and per-field messages in `data`.

### POST /api/v1/auth/login

Request:

```json
{
  "email": "nishar@example.com",
  "password": "StrongPassword123!"
}
```

Success (`200`):

```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "access_token": "<jwt>",
    "user": { "id": 1, "name": "Nishar", "email": "nishar@example.com", "role": "member" }
  },
  "error": null
}
```

An unknown email and an incorrect password both return the same `401` response (`error.code = "INVALID_CREDENTIALS"`), so account existence is never revealed.

### GET /api/v1/users/me

Requires `Authorization: Bearer <access_token>`.

Success (`200`):

```json
{
  "success": true,
  "message": "User retrieved successfully",
  "data": { "id": 1, "name": "Nishar", "email": "nishar@example.com", "role": "member" },
  "error": null
}
```

A missing, invalid, or expired token returns `401` in the standard error envelope (`error.code` is `"UNAUTHORIZED"` or `"TOKEN_EXPIRED"`).

Project and task CRUD endpoints are not yet implemented and will be documented here as they land.

## License

MIT
