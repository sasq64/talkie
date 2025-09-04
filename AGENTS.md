# Repository Guidelines

## Project Structure & Module Organization
- `talkie/`: Core Python package (entry: `talkie.__main__`), rendering, IF integration, TTS, and config. Assets in `talkie/data/` (fonts, prompts, native `l9` binary).
- `tools/`: C/CMake tools (Level 9 interpreter and utilities). Built outputs are copied to `talkie/data/l9`.
- `tests/`: Pytest suite (`test_*.py`).
- `games/`: Sample game files for local runs.
- Root helpers: `build.py` (CMake build wrapper), `pyproject.toml` (deps, tooling), `README.md`, `DESIGN.md`.

## Build, Test, and Development Commands
- Create env: `python -m venv .venv && source .venv/bin/activate`
- Install (dev): `pip install -e .[dev,test]`
- Build native tools (requires CMake + C compiler): `python build.py`
  - Copies Level 9 binary to `talkie/data/l9`.
- Run app: `python -m talkie games/zork.z3` or `talkie --help`
- Tests: `pytest` (coverage: `htmlcov/index.html`)
- Lint/format: `ruff check . && black . && isort .`
- Type check: `pyright`

## Coding Style & Naming Conventions
- Python 3.12, Black line length 88, isort profile “black”.
- Ruff rules enabled (pycodestyle/pyflakes/bugbear/pyupgrade/etc.); fix before PR.
- Naming: modules/functions `snake_case`, classes `CamelCase`, constants `UPPER_CASE`.
- Keep package layout under `talkie/` and tests in `tests/`.

## Testing Guidelines
- Framework: `pytest` with coverage (`--cov=talkie`).
- Location/patterns: `tests/test_*.py`, classes `Test*`, functions `test_*`.
- Marks: use `@pytest.mark.slow` or `@pytest.mark.integration`; deselect with `-m "not slow"`.
- Prefer unit tests near affected modules; include edge cases and regression cases.

## Commit & Pull Request Guidelines
- Commits: short, imperative summaries (e.g., “Refactor layout handling”, “Fix draw overflow”).
- PRs must include: clear description, rationale, screenshots/GIFs for UI changes, test coverage for new behavior, and notes if `tools/` or native build changed.
- CI expectations: ruff/black/isort clean, pyright passes, pytest green.

## Security & Configuration Tips
- OpenAI key: store in `~/.openai.key` (single line). Do not commit keys; avoid printing prompts/responses in logs.
- Config: runtime options via CLI (see `talkie/talkie_config.py`), prompts in `talkie/data/prompts.yaml`.
