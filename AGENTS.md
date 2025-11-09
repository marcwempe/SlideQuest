# SlideQuest Agent Brief

This document is exclusively for automation agents. Keep the human-facing context in `README.md` (English) and `Liesmich.md` (Deutsch) untouched.

## Scope
- Work only inside `src/slidequest`, `assets`, `data`, and root-level docs unless the user explicitly extends the scope.
- Never touch legacy folders or external repos without confirmation.
- Keep commits incremental; destructive git commands are forbidden unless the user instructs otherwise.

## Principles
- Prefer simple, low-complexity code and small, focused files.
- Treat every component as a reusable module with explicit inputs/outputs.
- Ask the user whenever a request is ambiguous.
- Track large or multi-step requests in `Tasks.md` before coding.
- Documentation split: `README.md` (EN) + `Liesmich.md` (DE) for humans, `AGENTS.md` + `Tasks.md` for technical/agent content -- keep them up to date.
- When asked to tint layouts for validation, use bold, high-contrast colors.
- All user-facing strings must remain i18n-ready and follow the OS locale (German UI on German systems).

## Tooling
- Use `uv` (`uv add`, `uv sync`, `uv run`) or the equivalent `make run|dev|sync`.
- Launch the GUI via `uv run slidequest`; for hot reload use `uv run slidequest-dev` or `make dev`.
- Prefer `rg` for search; stay ASCII unless a file already uses Unicode.
- CI runs `uv sync --all-groups`, `flake8`, and `pytest` (see `.github/workflows/python.yml`). Ensure those commands succeed locally when relevant.

## Coding Guidelines
- Entry point: `src/slidequest/app.py` stays minimal -- just bootstrap Master + Presentation windows. Business logic belongs in `src/slidequest/views/master_window.py` (UI composition), `src/slidequest/views/presentation_window.py` (rendering), `src/slidequest/viewmodels/...` (state/persistence), and helpers under `src/slidequest/services/...`, `src/slidequest/utils/...`, `src/slidequest/views/widgets/...`. Preserve this separation whenever you add features.
- Keep every Python module between **200–800 lines**; when a file grows beyond that window, split it into focused mixins or helpers instead of letting it bloat.
- Master/detail widgets should delegate all state mutations to the relevant ViewModel/Service; avoid new persistence or content helpers inside the view classes.
- Persist slide content in `data/slides.json`. Whenever layouts or dropped media change, rerender the `PresentationWindow` to update `assets/thumbnails/...`.
- Shared config/notes live in root markdown files; add inline comments only to clarify non-obvious logic.
- Icons must adapt to light/dark themes (light icons on dark backgrounds, dark icons on light backgrounds).
- Tooltips must expose unique IDs for every control to aid documentation.
- Der Layout-Detail-Header bleibt frei von Formularfeldern; Explorer-Slide-Items müssen beim Hover/bei Aktivierung optisch reagieren (Akzent-Border + Hover-Hintergrund).

## Communication
- Summaries lead with the "why," then the "what," followed by TODOs/follow-ups.
- Stop immediately if a command touches unexpected files or if instructions are unclear, and ask the user for guidance.
