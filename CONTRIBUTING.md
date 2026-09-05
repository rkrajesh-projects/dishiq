# Contributing to DishIQ

We welcome contributions to the DishIQ project! Please follow these guidelines to get your development environment set up and to ensure a smooth review process.

## Development Setup

The easiest way to run the full application stack is using Docker Compose:

1. Clone the repository.
2. Create your `.env` file based on `.env.example`.
3. Build and start the services:
   ```bash
   docker compose up --build
   ```

If you prefer to run services locally (without Docker) for faster iteration, you can run the backend and frontend separately:
- **Backend**: `cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000` (ensure PostgreSQL is running locally).
- **Frontend**: `cd frontend && npm install && npm run dev`

## Running Tests

Before submitting a Pull Request, ensure all tests pass. Run the test suites for the respective components you've modified:

- **Backend**: `cd backend && pytest`
- **Frontend**: `cd frontend && npm test`
- **MCP Server**: `cd mcp-server && pytest`
- **E2E Tests**: `cd e2e && npx playwright test`

## Pull Request Guidelines

To help us review and merge your changes efficiently, please ensure your PR meets the following expectations:

- **Clear Description**: Describe what your PR changes, why it is needed, and any context the reviewer might need.
- **Passing Tests**: Ensure all existing tests pass and write new tests for any added features or bug fixes.
- **Scoped Changes**: Keep your PR focused on a single feature, bug fix, or refactor. Avoid unrelated changes.
- **Code Quality**: Ensure the code follows existing formatting and style guidelines.
