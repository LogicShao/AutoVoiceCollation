# Repository Guidelines

## Multi-Agent Collaboration Model

This project uses a **layered agent system** for plan-driven development. Two roles interact with the codebase:

### Orchestrator (Atlas / Sisyphus)

The Orchestrator **never writes code directly** outside `.sisyphus/`. It:
- Reads `.sisyphus/plans/*.md` — parses task checkboxes, builds dependency graph
- Breaks plan tasks into granular sub-tasks and registers them as todo items
- Delegates each atomic task to a **Subagent** via structured prompts (7 elements — see [Delegation Protocol](#delegation-protocol))
- Runs independent tasks in parallel by invoking multiple subagents in one message
- **Verifies** every subagent output through a mandatory 4-phase gate before marking any task complete:
  1. **Read** every changed file — understand what each line does
  2. **Run** `ruff check` + `pytest` on changed modules
  3. **QA** user-facing changes hands-on (curl for API, browser for UI, REPL for library code)
  4. **Gate** — only proceed if all three: `code understood AND tests pass AND QA passed`
- Batch-reports completed tasks to the Maintainer for approval
- Tracks workspace state in `.sisyphus/boulder.json` and `.sisyphus/notepads/`
- Failure recovery: resumes the **same subagent session** (`session_id`) — never starts fresh on a follow-up

### Subagent (Sisyphus-Junior / explore / oracle / librarian)

A Subagent receives **one atomic task** per delegation and:
- Executes within a clearly defined scope (files, functions, constraints)
- Follows TDD: write failing tests first (RED) → minimal implementation (GREEN) → refactor
- Self-validates: `ruff check` + `pytest` + `lsp_diagnostics` MUST all pass before reporting "done"
- Records findings in `.sisyphus/notepads/<plan>/learnings.md` (append, never overwrite)
- Reports blockers to `.sisyphus/notepads/<plan>/issues.md` instead of stopping
- Does NOT interact with the Maintainer directly — all communication goes through the Orchestrator
- Must NOT modify files outside its delegated scope

### Execution Flow

```
Maintainer approves plan
         ↓
Orchestrator reads plan → breaks into sub-tasks → registers todos
         ↓
┌─ Wave 1 (parallel) ──────────────────────┐
│ Subagent A ──┐    Subagent B ──┐         │
│ (Task 1)     │    (Task 2)     │  ...    │
│    ↓         │       ↓         │         │
│ Verify       │    Verify       │         │
└──────────────┴─────────────────┴─────────┘
         ↓
┌─ Wave 2 (depends on Wave 1) ─────────────┐
│ Subagent C ──┐    Subagent D ──┐         │
│ (Task 4)     │    (Task 6)     │         │
└──────────────┴─────────────────┴─────────┘
         ↓
Orchestrator batch-report → Maintainer approves
```

---

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

### Automated Validation Gate (MANDATORY for Subagent)

**Before any Subagent reports "done", it MUST self-verify:**

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

5. Never use emoji or special Unicode symbols (e.g., `✅ ❌ ⚠️ ✨ 🎯`) in logger output, print statements, error messages, or any text that appears in terminal/API responses. These characters break on CJK-unaware terminals and logging pipelines. Use plain ASCII alternatives like `[OK]`, `[WARN]`, `[ERR]`, `->`, etc.

**Failure to pass any of these checks = task NOT complete. Do NOT report "done".**

### Orchestrator Verification (MANDATORY after every delegation)

Subagents often claim "done" when code has errors. The Orchestrator is the QA gate:

1. **Read** EVERY changed file line-by-line — understand what each line does
2. **Run** `ruff check` + `pytest` for the changed modules (not just trusting subagent output)
3. **Cross-check** subagent claims vs actual code — if `git diff` shows unexpected scope, reject
4. **Hands-on QA** for user-facing changes: curl for APIs, browser for UI, REPL for libraries
5. **Gate**: only proceed if `code understood AND tests pass AND QA passed`

If verification fails — **resume the same subagent session** via `session_id`, do NOT start fresh.

### Maintainer Review Workflow

The Orchestrator batches completed tasks for maintainer approval:

1. **Batch report**: after a wave of tasks passes Orchestrator verification, state "功能完成，等待人工验收" with a summary of ALL changes in that batch
2. **Wait for approval**: the Orchestrator may continue verifying independent tasks but must NOT mark batch as approved until the Maintainer replies
3. **After approval**: the Orchestrator updates all tasks in the batch to "功能验收通过"

This allows parallel task execution while keeping the Maintainer in the review loop.

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

## Delegation Protocol

When the Orchestrator delegates to a Subagent, the prompt MUST include these 7 elements:

```
1. TASK — exact checkbox item, no ambiguity
2. EXPECTED OUTCOME — files created/modified, behavior, verification command
3. REQUIRED TOOLS — specific tools and what to search/check
4. MUST DO — patterns to follow, tests to write, notepad to append
5. MUST NOT DO — scope boundaries, forbidden patterns, guardrails
6. CONTEXT — notepad paths (READ/WRITE), inherited wisdom, dependencies
7. REFERENCES — exact file paths with line numbers
```

**Scope Rules**:
- One atomic task per delegation — never batch multiple plan items into one prompt
- Subagent must NOT modify files outside its explicitly delegated scope
- Subagent must NOT introduce new dependencies unless explicitly permitted

**Failure Recovery**:
- Always resume the same subagent session (`session_id`) for fixes/follow-ups
- The subagent already has full context — restarting from scratch wastes 70%+ tokens
- Maximum 3 retries per task; if still blocked, document in `issues.md` and move on

**Specialist Selection**:
- `explore` agent: codebase search / pattern discovery (always run in background)
- `librarian` agent: remote repo analysis / official docs / GitHub examples (always run in background)
- `oracle` agent: read-only architecture / debugging consultation
- `category=deep` subagent: autonomous multi-file implementation with TDD
- `category=quick` subagent: single-file changes, typo fixes, trivial modifications
- `category=visual-engineering` subagent: frontend, UI/UX, styling, design, animation

## Workspace State (.sisyphus/)

The `.sisyphus/` directory is the persistent workspace for plan-driven development:

```
.sisyphus/
├── boulder.json           # Active plan, session tracking, task→session mapping
├── plans/*.md             # Prometheus-generated execution plans with checkboxes
├── notepads/<plan>/
│   ├── learnings.md       # Patterns, conventions, successful approaches (append)
│   ├── decisions.md       # Architectural choices made during execution
│   └── issues.md          # Problems, blockers, known gotchas
├── evidence/              # QA scenario execution evidence (per-task)
│   ├── task-1-<slug>.txt
│   └── task-2-<slug>.txt
└── drafts/                # Temporary work artifacts
```

**Rules**:
- **Orchestrator** may READ/WRITE `.sisyphus/` files directly
- **Subagent** must APPEND to notepads (never overwrite) and CREATE evidence files
- `boulder.json` tracks session_ids for resumability — never delete it mid-plan
- When completing a task: Orchestrator marks `- [x]` in the plan file AND updates `boulder.json`

## Single Source Of Truth

- `AGENTS.md` is the authoritative repository instruction file for coding agents.
- `CLAUDE.md` is only a lightweight pointer document for Claude-specific entry guidance.
- If `CLAUDE.md` and `AGENTS.md` ever differ, always follow `AGENTS.md`.
- When updating agent rules, update `AGENTS.md` first and keep `CLAUDE.md` as a reference to it rather than duplicating full rules.
