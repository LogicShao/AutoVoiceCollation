# Repository Guidelines

## Project Structure & Module Organization

- `api.py`: FastAPI app (serves API + web UI).
- `main.py`: CLI entry point for local processing.
- `src/`: Python package code (`core/`, `services/`, `utils/`, `text_arrangement/`, `api/`).
- `frontend/`: Static UI sources (`frontend/src/`) and built assets (`frontend/dist/`).
- `tests/`: Pytest suite (see `pytest.ini` for discovery/markers).
- `docs/`, `assets/`: Documentation and static assets (icons, screenshots).
- `out/`, `download/`, `temp/`, `logs/`: runtime/generated artifacts (don't commit large outputs).

## Build, Test, and Development Commands

- Python deps: `python -m venv venv` then `pip install -r requirements.txt`.
- Configure: copy `.env.example` to `.env` and set required API keys.
- Run API server: `python api.py` (docs at `http://localhost:8000/docs`).
- Run CLI: `python main.py` (examples in `README.md`).
- Frontend CSS (Tailwind): `npm install` then `npm run dev` (watch) or `npm run build`.
- Docker (recommended): `scripts/docker-start.sh start` (Linux/Mac) or `scripts/docker-start.bat start` (Windows).

## Coding Style & Naming Conventions

- Follow `.editorconfig` (Python: 4 spaces; JS/CSS/HTML: 2 spaces; LF line endings).
- Python quality gate: Ruff (`ruff check .` and `ruff format .`), configured in `ruff.toml`.
- Convenience: `scripts/lint.sh [check|fix|format|all]` or `scripts/lint.bat [check|fix|format|all]`.

## Testing Guidelines

- Install test deps: `pip install -r requirements-test.txt`.
- Run: `pytest` (unit tests by default). CI smoke test uses: `pytest tests/test_api.py -k "not Background"`.
- Use markers from `pytest.ini` (e.g., `-m integration`) only when local secrets/services are configured.

## Commit & Pull Request Guidelines

- Commit style follows Conventional Commits: `feat: ...`, `fix: ...`, `refactor: ...`, `docs: ...`, `ci: ...` (optional scopes like `feat(api): ...`).
- PRs: describe the change, link issues, update `.env.example` when adding config, and include UI screenshots for frontend changes.
- Before opening: run `pytest` and `ruff` checks; run `npm run build` if you touched `frontend/src/css/input.css` or Tailwind config.

## Security & Configuration Tips

- Never commit `.env` or API keys; use `.env.example` as the public template.
- Prefer small, reviewable changes; keep generated output (PDFs/zips) out of git history.

## Agent Workflow (Approval Required)

- Before any repo-writing action (patches, write commands, branches/commits), provide a complete proposal: goal, affected files, steps/commands, validation, and rollback.
- Wait for explicit approval by the maintainer replying with the token `OJBK` before making changes.
- For risky or multi-file changes, propose using a dedicated branch (e.g., `agent/YYYY-MM-DD-short-desc`); proceed only if approved.
