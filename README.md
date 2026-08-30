# Enterprise Task Management API

A production-oriented REST API for managing users, projects, and tasks, built with Flask and structured around clean, testable, service-oriented layers. This project demonstrates backend engineering practices — application factory pattern, layered architecture, centralized error handling, and consistent API response contracts — intended as a portfolio-quality reference implementation.

## Overview

The API is being built incrementally, milestone by milestone. The foundation establishes the production-oriented application architecture: configuration management, database models, error handling, a consistent response envelope, and a health check endpoint. JWT-based user authentication, full Project CRUD, and full Task CRUD are implemented with ownership-based authorization.

## Tech Stack

- **Python 3.11+**
- **Flask** — web framework
- **Flask-SQLAlchemy** — ORM
- **Flask-Migrate** — database migrations (Alembic)
- **Flask-JWT-Extended** — JWT authentication (registration, login, and bearer-token-protected endpoints implemented)
- **Marshmallow** — request/response validation (schemas implemented alongside their respective endpoints)
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
├── routes/         # Flask blueprints for health, auth, users, projects, and tasks
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
- Full Project CRUD (`POST/GET/PATCH/DELETE /api/v1/projects`) protected by JWT bearer authentication, with strict ownership-based authorization: only a project's owner can view, update, or delete it — including admins and managers, whose roles grant no bypass. Deleting a project cascades to delete its tasks.
- Full Task CRUD protected by JWT bearer authentication. Tasks are created and listed under their parent Project, and only that Project's owner can create, list, view, update, or delete them. Assignment does not grant access, and roles do not bypass ownership.
- Consistent JSON success/error response envelope for every HTTP error (400, 404, 405, 500, etc.), not just the happy path
- Centralized error handling: all Werkzeug HTTP exceptions return the standard JSON envelope, and unexpected server errors return a generic 500 with no internal stack trace exposed
- JWT error handling (missing/invalid/expired tokens) also returns the standard JSON envelope instead of Flask-JWT-Extended's default format
- Fail-fast production configuration: `SECRET_KEY`, `JWT_SECRET_KEY`, and `DATABASE_URL` are required (no insecure fallback values) when `FLASK_ENV=production`

## Planned Features

- Role-based access control
- API documentation
- Pagination and filtering for list endpoints

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
| POST   | `/api/v1/projects`       | Yes (Bearer JWT) | Creates a project owned by the authenticated user |
| GET    | `/api/v1/projects`       | Yes (Bearer JWT) | Lists projects owned by the authenticated user |
| GET    | `/api/v1/projects/<id>`  | Yes (Bearer JWT) | Returns a project (owner only) |
| PATCH  | `/api/v1/projects/<id>`  | Yes (Bearer JWT) | Partially updates a project (owner only) |
| DELETE | `/api/v1/projects/<id>`  | Yes (Bearer JWT) | Deletes a project and its tasks (owner only) |
| POST   | `/api/v1/projects/<project_id>/tasks` | Yes (Bearer JWT) | Creates a task in an owned project |
| GET    | `/api/v1/projects/<project_id>/tasks` | Yes (Bearer JWT) | Lists tasks in an owned project |
| GET    | `/api/v1/tasks/<task_id>` | Yes (Bearer JWT) | Returns a task (parent project owner only) |
| PATCH  | `/api/v1/tasks/<task_id>` | Yes (Bearer JWT) | Partially updates a task (parent project owner only) |
| DELETE | `/api/v1/tasks/<task_id>` | Yes (Bearer JWT) | Deletes a task (parent project owner only) |

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

### Projects

All project endpoints require `Authorization: Bearer <access_token>` and enforce **ownership-based authorization**: a project may only be viewed, updated, or deleted by the user in its `owner_id`. This applies regardless of `role` — `admin` and `manager` do not bypass ownership. There is no project-membership concept yet; only the owner has any access.

#### POST /api/v1/projects

Request:

```json
{
  "name": "Website Redesign",
  "description": "Q4 marketing site refresh"
}
```

- `name` is required, 1–150 characters (trimmed).
- `description` is optional and nullable.
- The authenticated user becomes `owner_id`.

Success (`201`):

```json
{
  "success": true,
  "message": "Project created successfully",
  "data": {
    "id": 1,
    "name": "Website Redesign",
    "description": "Q4 marketing site refresh",
    "owner_id": 1,
    "created_at": "2026-08-30T00:00:00+00:00",
    "updated_at": "2026-08-30T00:00:00+00:00"
  },
  "error": null
}
```

Invalid input (missing/blank `name`) returns `400` with `error.code = "VALIDATION_ERROR"`. A non-JSON body returns `400` with `error.code = "INVALID_JSON"`.

#### GET /api/v1/projects

Returns only projects owned by the authenticated user.

Success (`200`):

```json
{
  "success": true,
  "message": "Projects retrieved successfully",
  "data": [
    { "id": 1, "name": "Website Redesign", "description": "Q4 marketing site refresh", "owner_id": 1, "created_at": "...", "updated_at": "..." }
  ],
  "error": null
}
```

#### GET /api/v1/projects/\<id\>

Success (`200`): same shape as the `POST` response's `data` object.

- Unknown `id` returns `404` with `error.code = "NOT_FOUND"`.
- An `id` that belongs to another user returns `403` with `error.code = "FORBIDDEN"`.

#### PATCH /api/v1/projects/\<id\>

Request (any subset of these fields, at least one required):

```json
{
  "name": "Website Redesign 2.0",
  "description": "Updated scope"
}
```

Success (`200`): same shape as the `POST` response's `data` object, reflecting only the fields that were provided.

- An empty body returns `400` with `error.code = "VALIDATION_ERROR"`.
- Unknown `id` returns `404` with `error.code = "NOT_FOUND"`.
- An `id` that belongs to another user returns `403` with `error.code = "FORBIDDEN"` and leaves the project unchanged.

#### DELETE /api/v1/projects/\<id\>

Deletes the project and, via cascade, all of its tasks. There is no soft delete.

Success (`200`):

```json
{
  "success": true,
  "message": "Project deleted successfully",
  "data": null,
  "error": null
}
```

- Unknown `id` returns `404` with `error.code = "NOT_FOUND"`.
- An `id` that belongs to another user returns `403` with `error.code = "FORBIDDEN"` and leaves the project (and its tasks) intact.

### Tasks

All Task endpoints require `Authorization: Bearer <access_token>`. Authorization is inherited from the parent Project: only the user whose ID matches `project.owner_id` can manage the Project's Tasks. An assigned user does not gain Task access, and `admin` or `manager` roles do not bypass ownership.

#### POST /api/v1/projects/\<project_id\>/tasks

Request:

```json
{
  "title": "Prepare launch checklist",
  "description": "Confirm deployment and rollback steps",
  "status": "in_progress",
  "priority": "high",
  "assigned_to": 2
}
```

- `title` is required, trimmed, and must contain 1–200 characters.
- `description` is optional and nullable.
- `status` defaults to `pending`; accepted values are `pending`, `in_progress`, and `completed`.
- `priority` defaults to `medium`; accepted values are `low`, `medium`, and `high`.
- `assigned_to` is optional and nullable. It must identify an existing user. Assignment does not grant access.
- `project_id` comes from the URL and cannot be changed through Task updates.

Success (`201`):

```json
{
  "success": true,
  "message": "Task created successfully",
  "data": {
    "id": 1,
    "title": "Prepare launch checklist",
    "description": "Confirm deployment and rollback steps",
    "status": "in_progress",
    "priority": "high",
    "project_id": 1,
    "assigned_to": 2,
    "created_at": "2026-08-30T00:00:00+00:00",
    "updated_at": "2026-08-30T00:00:00+00:00"
  },
  "error": null
}
```

An unknown Project returns `404`. Another user's Project returns `403`. Invalid input returns `400` with `error.code = "VALIDATION_ERROR"`; malformed JSON returns `400` with `error.code = "INVALID_JSON"`.

#### GET /api/v1/projects/\<project_id\>/tasks

Returns all Tasks belonging to the owned Project as a JSON array. An empty Project returns an empty array. An unknown Project returns `404`, while another user's Project returns `403`.

#### GET /api/v1/tasks/\<task_id\>

Returns the Task representation shown in the create response. An unknown Task returns `404`; a Task whose parent Project belongs to another user returns `403`.

#### PATCH /api/v1/tasks/\<task_id\>

Accepts any non-empty subset of `title`, `description`, `status`, `priority`, and `assigned_to`. Set `description` or `assigned_to` to `null` to clear it. The parent Project cannot be changed.

Success (`200`) returns the updated Task. Empty or invalid input returns `400` with `error.code = "VALIDATION_ERROR"`; an unknown Task returns `404`; another user's Task returns `403` and remains unchanged.

#### DELETE /api/v1/tasks/\<task_id\>

Deletes the Task without deleting its parent Project.

Success (`200`):

```json
{
  "success": true,
  "message": "Task deleted successfully",
  "data": null,
  "error": null
}
```

An unknown Task returns `404`; another user's Task returns `403` and remains unchanged.

## License

MIT
