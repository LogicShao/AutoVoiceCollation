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

### Python Environment (CRITICAL)

**System Python is strictly forbidden** (e.g., `/usr/bin/python3`, `/usr/bin/python`, `python3`, etc.).

This project uses a Windows conda environment:
- **Windows path**: `D:\conda_envs\autovoicecollation\python.exe`
- **WSL path**: `/mnt/d/conda_envs/autovoicecollation/python.exe`
- **Python version**: 3.11.15

**Mandatory rule: Before any Python operation, you MUST ask the user to confirm which Python environment to use.**
Do NOT assume or use any Python path (including the conda paths above) unless explicitly told by the user.

All Python commands must use the user-specified Python:
```bash
# Correct — after user confirmation
/path/user/specified/python -m pytest tests/

# Wrong — strictly forbidden
python3 -m pytest tests/
pip install xxx
pip install --break-system-packages xxx
```

When installing new dependencies in WSL, install to the user-specified Python environment:
```bash
/path/user/specified/python -m pip install <package>
```

**Forbidden operations**:
- `pip install --break-system-packages` — pollutes the OS Python
- `pip install` without `--user` — installs to system paths by default
- Using `python3` / `/usr/bin/python3` to run project code or tests
- Choosing or using any Python path without user confirmation

## Coding Style & Naming Conventions

- Follow `.editorconfig` (Python: 4 spaces; JS/CSS/HTML: 2 spaces; LF line endings).
- Python quality gate: Ruff (`ruff check .` and `ruff format .`), configured in `ruff.toml`.
- Convenience: `scripts/lint.sh [check|fix|format|all]` or `scripts/lint.bat [check|fix|format|all]`.

### Post-Write Validation (MANDATORY)

**After every code change, you MUST verify correctness before marking a task as done:**

1. Run Ruff on changed files:
   ```bash
   ruff check path/to/changed/file.py
   ```
   Fix all errors (F821 undefined names, F401 unused imports, E999 syntax errors).

2. Run LSP diagnostics on changed files (or the parent directory if multiple files).

3. Run `pytest` to verify no regressions:
   ```bash
   /mnt/d/conda_envs/autovoicecollation/python.exe -m pytest tests/ -x -q
   ```

4. Never suppress type errors with `as any`, `@ts-ignore`, or `@ts-expect-error`.

**Failure to pass any of these checks = task NOT complete.**

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

## Single Source Of Truth

- `AGENTS.md` is the authoritative repository instruction file for coding agents.
- `CLAUDE.md` is only a lightweight pointer document for Claude-specific entry guidance.
- If `CLAUDE.md` and `AGENTS.md` ever differ, always follow `AGENTS.md`.
- When updating agent rules, update `AGENTS.md` first and keep `CLAUDE.md` as a reference to it rather than duplicating full rules.
