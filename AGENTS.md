# SlideQuest Agent Brief

Guidelines for Codex/AI collaborators that hold across sessions.

## Scope

- `src/slidequest` contains the new PySide6 stack. Keep all new Python modules inside this package.
- `MTMT` and `MTMTContent` are legacy and must stay untouched unless the user explicitly instructs otherwise.
- Favor incremental, well-explained commits; destructive git commands are off-limits.

## Tooling

- Use **uv** for dependency management: `uv add`, `uv sync`, `uv run ...`.
- Run the GUI via `uv run slidequest`. Use `uv run slidequest-dev` for automatic reloads powered by `watchfiles`.
- Prefer `rg` for searches and keep files ASCII unless they already contain Unicode glyphs.

## Coding patterns

- UI entry point lives in `src/slidequest/app.py`. Keep widgets/components modular to simplify later migration to the production client.
- New configuration or shared instructions belong in markdown files at the repository root so they are easy to discover.
- Add concise comments only when the intent is not obvious from the code.

## Communication

- Summaries should highlight the *why* behind changes before diving into the *what*.
- Call out TODOs or follow-up ideas explicitly so the next session can pick them up quickly.
- If unexpected files change (e.g., external tooling rewrites), pause and ask the user before proceeding.
