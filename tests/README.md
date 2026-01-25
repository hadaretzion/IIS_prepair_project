# PrepAIr Testing Guide

This directory contains backend and frontend tests covering unit, integration, and workflow scenarios.

## Structure

- `tests/backend/`: pytest tests for FastAPI backend
- `tests/frontend/`: Jest/RTL tests for React frontend

## Backend Tests

### Run all backend tests

```
pytest tests/backend/
```

### Run with coverage

```
pytest tests/backend/ --cov=backend --cov-report=term-missing
```

### Notes

- Tests use a temporary SQLite database per test run.
- Gemini API calls are mocked where needed.

## Frontend Tests

### Install dependencies

```
cd app
npm install
```

### Run frontend tests

```
cd app
npm test
```

### Run with coverage

```
cd app
npm test -- --coverage
```

### Notes

- Frontend tests are located in `tests/frontend/`.
- API calls are mocked in tests to avoid live backend dependencies.

## Coverage Goals

- Backend: 80%+ overall, 100% critical flows (CV analysis, interview flow)
- Frontend: 70%+ overall, 100% critical flows (setup, CV improve, interview)
