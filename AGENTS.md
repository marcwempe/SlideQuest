# SlideQuest Agent Brief

## Scope
- Build in `src/slidequest`; leave `MTMT*` untouched unless the user says otherwise.
- Keep commits incremental and avoid destructive git.
- `MTMT/` carries its own `.git`; only add it here (as a submodule) if explicitly requested.

## Principles
- Prefer simple code and keep cognitive complexity low.
- Favor smaller, focused files over large ones.
- Ask the user before acting if their request is ambiguous.
- Keep `AGENTS.md` and `README.md` current; AGENTS is AI-only, README summarizes the handbook in `docs/`.
- If a request implies a large change, capture it in `Tasks.md`, split it into prompt-sized subtasks, and tackle them incrementally.
- [IMPORTANT] Documentation must stay current: user-facing docs (e.g., `README.md`) are written in German (with umlauts), technical docs (`AGENTS.md`, `docs/`, `Tasks.md`) stay in English.
- Treat every component as a reusable module; design APIs and layouts so they work independently of the surrounding UI.
- When asked to color layout elements for validation, use bold, high-contrast colors so regions remain unmistakable.

## Tooling
- Use uv (`uv add`, `uv sync`, `uv run`) or the matching `make run|dev|sync` shortcuts.
- Launch the UI with `uv run slidequest`; hot reload via `uv run slidequest-dev` / `make dev`.
- Prefer `rg` for search and stay in ASCII unless a file already uses Unicode.

## Coding
- Entry point: `src/slidequest/app.py`. Keep widgets modular.
- Shared config/notes live in root markdown files; add comments only when intent is unclear.
- Maintain the two-window setup: `MasterWindow` (controls) + `PresentationWindow` (slides).

## Communication
- Summaries lead with the “why,” then the “what,” and list TODOs/follow-ups.
- Stop and ask if tools touch unexpected files or instructions are unclear.
