## SlideQuest (PySide6 Prototype)

This directory hosts the new SlideQuest prototype that will eventually replace the `MTMT*` legacy apps. The UI is built with **PySide6** and all dependencies are managed via **uv**.

### Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) installed globally (`pip install uv` or grab a release binary)

### Setup

```bash
uv sync
```

This creates a local `.venv` managed by uv.

### Daily commands

| Task | Command |
| --- | --- |
| Run the GUI once | `uv run slidequest` / `make run` |
| Run with hot-reload | `uv run slidequest-dev` / `make dev` |
| Add a dependency | `uv add <package>` |

The dev watcher uses `watchfiles` to restart the GUI whenever something inside `src/slidequest` or `pyproject.toml` changes.

Prefer the Make targets (`make run`, `make dev`, `make sync`) if you want shorter commands; they simply call the matching `uv` invocations.

### Project layout

- `src/slidequest/app.py` – entry window and future navigation logic.
- `src/slidequest/dev.py` – watchfiles-based dev loop.
- `AGENTS.md` – shared instructions for Codex / AI contributors.
- `MTMT*` – legacy Qt/C++ project; do not modify unless explicitly requested.

### Next steps

Use `src/slidequest` for new modules (e.g., slide parsing, data providers, layouting). The placeholder UI simply proves that the PySide6 stack is wired up, so you can start replacing it immediately.
