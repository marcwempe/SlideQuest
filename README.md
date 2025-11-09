# SlideQuest

PySide6 prototype for building and presenting mixed-media slides. SlideQuest ships two coordinated windows -- `MasterWindow` for control and `PresentationWindow` for projection -- and keeps every UI string i18n-ready so the runtime language follows the OS locale. The entire codebase is produced by OpenAI Codex sessions and is licensed under the GNU GPL v3.

## Tooling & Commands

- **Runtime**: Python 3.12+, [uv](https://docs.astral.sh/uv/) for dependency management.
- **Install**: `uv sync` (creates `.venv` and installs PySide6 + dev tools).
- **One-off run**: `uv run slidequest` or `make run`.
- **Hot reload**: `uv run slidequest-dev` / `make dev` (watchfiles-based).
- **Tests**: `make test` (runs pytest + Qt widgets headless via `QT_QPA_PLATFORM=offscreen`).
- **Add dependency**: `uv add <package>`.
- Prefer `rg` for file/text search; keep sources ASCII unless Unicode is already in use.
- **CI**: `.github/workflows/python.yml` installs uv, runs flake8, and executes pytest on every push/PR targeting `main`.

## Workspace Layout

- `src/slidequest/app.py` - thin entry point that wires Master/Presentation windows.
- `src/slidequest/models/...` - dataclasses for layouts and slides.
- `src/slidequest/viewmodels/...` - viewmodels (e.g., `MasterViewModel`) that mediate persistence and UI.
- `src/slidequest/services/storage.py` - JSON persistence helpers.
- `src/slidequest/views/master_window.py` - full `MasterWindow` implementation and supporting widgets.
- `src/slidequest/views/presentation_window.py` - secondary window that mirrors the active layout.
- `src/slidequest/views/widgets/layout_preview.py` - reusable layout canvas + cards.
- `src/slidequest/views/widgets/common.py` - shared UI helpers (flow layout, icon buttons).
- `src/slidequest/utils/media.py` - helpers for slug/asset path handling.
- `assets/` - design references + generated thumbnails (`assets/thumbnails/*.png`).
- `docs/assets/LayoutViewScreenshot.png` - latest UI snapshot used in documentation.
- `AGENTS.md` - operational rules for automation agents.

![Layout overview](docs/assets/LayoutViewScreenshot.png)

*MasterWindow anatomy: StatusBar, SymbolView (navigation), Explorer (header/main/footer), Detail view (header/main/footer + layout selection carousel).*

## Architecture

- `slidequest/app.py` boots a QApplication, instantiates `MasterWindow` + `PresentationWindow`, and wires them together.
- `MasterWindow` (in `views/master_window.py`) composes the UI, but delegates all persistence/state changes to `MasterViewModel`.
- `MasterViewModel` (`viewmodels/master.py`) uses `SlideStorage` (`services/storage.py`) to load/save `data/slides.json`, keep `layout.content` aligned with `images`, and emit change notifications.
- `PresentationWindow` mirrors the current layout purely for rendering/dropping thumbnails; only one instance exists at a time.
- Utilities such as `utils/media.py` (slug/path helpers) and `views/widgets/common.py` (FlowLayout/IconToolButton) keep reusable logic out of the windows.

## Slides & Data Model

Slides live in `data/slides.json` and follow this structure:

```json
{
  "slides": [
    {
      "title": "My Slide",
      "subtitle": "Layout Example",
      "group": "My Group",
      "layout": {
        "active_layout": "2S|60:40#1:40#2/1R:100/1R:100",
        "thumbnail_url": "assets/thumbnails/example.png",
        "content": [
          "media/image.png",
          "media/photo.jpg",
          "media/video.mp4"
        ]
      },
      "audio": {
        "playlist": ["media/music.mp3"],
        "effects": ["media/effect.ogg"]
      },
      "notes": {
        "notebooks": ["notes/show.md"]
      }
    }
  ]
}
```

- `layout.content[i]` corresponds to area `#i+1` in the active layout description. Layout changes never delete surplus media; unused items reappear when a compatible layout is chosen again.
- Layout descriptions may assign explicit area IDs via `#`, e.g. `25#1` to mark the first slot as the “primary” area. When such IDs exist, they dictate the order in which `layout.content` is mapped.
- `MasterViewModel` always keeps `layout.content` and `images` in sync; when the JSON omits `content`, defaults from `LAYOUT_ITEMS` are injected. Persisting runs through `SlideStorage`, which also ensures `assets/thumbnails` exists.
- Drag & drop in the Detail Preview updates `layout.content`, syncs the Presentation window, and captures a fresh thumbnail stored under `assets/thumbnails/<slug>.png`.
- Layout presets are defined in `src/slidequest/models/layouts.py`; each card in the Detail footer is built from these specs.

## Status & Navigation Surfaces

- **SymbolView** (left) exposes launchers for Layout, Audio, Notes, Files. Currently only the Layout button is wired (Explorer/Detail panels hide when it’s deselected); the other buttons serve as placeholders until their subapps exist. Active buttons get a left accent.
- **StatusBar** (top) groups artwork/title placeholders, transport controls (shuffle, previous, play/pause, stop, next, loop), seek bar, and volume cluster (mute, down, slider, up). These controls only update UI state for now (no audio backend).
- **PresentationWindow** is hidden until explicitly launched via the window button anchored at the bottom of SymbolView. Only one presentation window exists at a time; once it closes, the launcher re-enables.

## Localization & Accessibility

- Every button, slider, or input exposes a tooltip with its unique ID to simplify documentation/automation steps.
- UI strings are currently hard-coded, so keep them short and ready for future localization (German UI when the OS locale is German).
- Icons from Bootstrap SVG packs (`assets/icons/bootstrap/<domain>/...`) are tinted at runtime so they remain visible in light/dark palettes.

## Provenance & License

- SlideQuest is authored entirely by OpenAI Codex; no human-written legacy code remains.
- Source code is distributed under the **GNU General Public License v3.0**. See `LICENSE` for the full text and obligations when redistributing modified copies.
- Contributions should retain this license, respect the localization rules, and document changes in both README (en) and `Liesmich.md` (de).

## Git Workflow

1. **Sync & Branch** - Update `main` (`git pull origin main`) and start a feature branch (`git checkout -b feature/<topic>`). Avoid committing directly to `main`.
2. **Focused Work** - Keep change sets small, update documentation/localization alongside code, and surface large scopes before implementation.
3. **Test Locally** - Run `uv run slidequest` or `make dev`; add targeted checks for regressions when possible.
4. **Curate Staging** - Use `git status` plus `git add -p` to stage only intentional edits; generated assets (e.g., thumbnails) should be confirmed before inclusion.
5. **Commit Message** - Present-tense summary with context ("Add horizontal layout selector"). Reference related tasks if applicable.
6. **Push & Review** - `git push -u origin feature/<topic>` and open a PR against `main`, noting i18n/doc updates.
7. **Merge & Clean** - After review, merge (squash or fast-forward), delete the feature branch locally/remotely, and resync your workspace.
