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
- Consistent JSON success/error response envelope
- Centralized error handling for 400, 404, and 500 responses (no internal stack traces exposed)
- JWT extension configured and initialized (auth endpoints not yet implemented)

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
| `SECRET_KEY`     | Flask session signing secret                       | Yes (production) |
| `JWT_SECRET_KEY` | JWT signing secret                                 | Yes (production) |
| `DATABASE_URL`   | SQLAlchemy database URI (SQLite locally, PostgreSQL in production) | No (defaults to local SQLite) |

No secrets are committed to this repository. Development defaults are provided only where safe to do so.

## Running Tests

```bash
pytest
```

## API

| Method | Endpoint           | Description                  |
|--------|---------------------|-------------------------------|
| GET    | `/api/v1/health`    | Returns service health status |

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

Additional endpoints for authentication, users, projects, and tasks will be documented here as they are implemented.

## License

MIT
