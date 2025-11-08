# SlideQuest Handbook

> This Obsidian-friendly note captures the authoritative process details. The root `README.md` summarizes this file for quick reference.

## Development principles
- Prefer simple solutions over clever ones and keep cognitive complexity low.
- Split work into small, focused files/modules whenever possible.
- Confirm requirements with the user if anything is unclear before making changes.
- Keep `AGENTS.md` (AI instructions) and `README.md` (human-facing summary) in sync with the latest process.
- When a request balloons into a larger feature, log it in `Tasks.md`, break it into small prompts, and implement incrementally.
- Maintain language boundaries: user-facing docs (README, future guides) must be in German (with umlauts), while technical docs (this handbook, AGENTS, Tasks) stay in English for engineers new to the stack.
- Validation coloring rule: whenever the user asks to tint layout regions, pick vivid, clearly distinguishable colors to avoid ambiguity.
- Every UI component should be architected for standalone reuse (clean inputs/outputs, minimal coupling to global state).

## Tooling workflow
- Python 3.12 + `uv` manage dependencies and scripts (`uv add`, `uv sync`, `uv run ...`).
- `make run`, `make dev`, and `make sync` mirror the uv commands for convenience.
- `watchfiles` powers the hot-reload loop (`uv run slidequest-dev` / `make dev`).
- Use `rg` for searches and stick to ASCII unless a file already contains Unicode.

## UI windows
- `MasterWindow`: control surface for authoring/management tasks.
- `PresentationWindow`: slide output surface; keep it isolated from control logic.
- Both windows should launch together via `slidequest.main`.
- Reference layout: `assets/MasterWindow_GeneralLayout.png` documents the current MasterWindow subdivision (status bar, SymbolView, Explorer/Detail columns, and subviews).

## Directory guide
- `src/slidequest/app.py` – UI bootstrap and window wiring.
- `src/slidequest/dev.py` – watcher/orchestration of the dev loop.
- `AGENTS.md` – persistent AI guidance (not user-facing).
- `docs/` – Obsidian vault for the handbook and future notes.
- `MTMT*` – legacy application; treat as read-only unless explicitly tasked.

## Collaboration notes
- Document new conventions here first, then sync the README summary.
- Surface TODOs, blockers, or follow-up tasks at the end of each session.
- Avoid destructive git commands; `MTMT/` keeps its own repository and should only be re-added as a submodule when instructed.
- Use `Tasks.md` to queue multi-step efforts so future prompts stay focused.
- **IMPORTANT:** Keep every piece of documentation up to date immediately after changes; stale docs break the handoff contract.
