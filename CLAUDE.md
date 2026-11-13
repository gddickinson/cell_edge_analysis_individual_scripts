# Claude collaboration notes for `cell_edge_analysis_individual_scripts`

This project was built with substantial assistance from **Claude (Anthropic)**, primarily via **Claude Code**.

## Global preferences

George's global Claude preferences live in `~/.claude/CLAUDE.md` and apply to every project. Highlights:

- Keep all source files under 500 lines; split into focused modules if approaching that limit.
- For Python projects, maintain an `INTERFACE.md` at the project root as a navigation map of modules, classes, and key functions.
- Prefer many small, focused files over fewer large ones.
- Group related functionality; extract reusable logic into utility modules.

## Project navigation

See [`INTERFACE.md`](./INTERFACE.md) for a navigation map of this repository's modules and how they connect. Read `INTERFACE.md` before opening individual source files.

## Working with Claude on this repo

When directing Claude Code on this codebase, follow the global rules above, prefer making targeted edits via the `Edit` tool over rewriting whole files, and update `INTERFACE.md` whenever the project structure changes.

Project-specific conventions, build instructions, and lab-specific notes should be added below as the project evolves.

## Defaults, tests and the web interface

- Pipeline defaults live in `config.py` (`PIPELINE_CONFIG`); `run_all_steps.py` and the GUI use it, and every step
  script's own CONFIG must agree (`tests/test_defaults_single_source.py`). Never hardcode a default elsewhere.
- Tests: `python -m pytest -q tests` (includes the node tests of the JS ports). CI runs `tests/test_web.py`.
- After changing steps 1, 2, 5, 6, 7, `intensity_labels.py`, `fluorescence_edge_experiments/` or the demo data,
  regenerate the fixture (`python scripts/make_web_fixture.py`) and keep `web/static/*_engine.js` in step.
- The web app's demo data are synthetic; never put real recordings (the git-ignored `data/`) in `web/static/`.
