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
- `src/slidequest/services/project_service.py` - project-scoped storage (AppData, asset import/dedupe, trash handling).
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
- `MasterViewModel` (`viewmodels/master.py`) uses `SlideStorage` together with `ProjectStorageService` (`services/project_service.py`). Each project lives under the OS-specific AppData path (`…/SlideQuest/projects/<id>/project.json`) and stores slides plus a deduplicated `files` map.
- `PresentationWindow` mirrors the current layout purely for rendering/dropping thumbnails; only one instance exists at a time.
- Utilities such as `utils/media.py` (slug/path helpers) and `views/widgets/common.py` (FlowLayout/IconToolButton) keep reusable logic out of the windows.

## Slides & Data Model

Slides live inside `<AppData>/SlideQuest/projects/<id>/project.json` alongside a deduplicated `files` table:

```json
{
  "id": "demo",
  "files": {
    "9c7…": {"kind": "audio", "path": "audio/9c7….mp3", "hash": "…", "size": 123456},
    "1f4…": {"kind": "layouts", "path": "layouts/1f4….png", "hash": "…", "size": 98765}
  },
  "slides": [
    {
      "title": "My Slide",
      "layout": {
        "active_layout": "2S|60:40#1:40#2/1R:100/1R:100",
        "thumbnail_url": "layouts/thumbnails/example.png",
        "content": ["layouts/1f4….png", "layouts/8ab….png"]
      },
      "audio": {"playlist": ["audio/9c7….mp3"], "effects": []},
      "notes": {"notebooks": ["notes/42c….md"]}
    }
  ]
}
```

- `layout.content[i]` corresponds to area `#i+1` in the active layout description. Layout changes never delete surplus media; unused items reappear when a compatible layout is chosen again.
- Layout descriptions may assign explicit area IDs via `#`. When such IDs exist, they dictate the order in which `layout.content` is mapped.
- `MasterViewModel` keeps `layout.content`/`images` in sync, imports new media via Hash/UUID, and writes updates straight into the project folder.
- Drag & drop in the Detail Preview imports media, syncs the Presentation window, and captures thumbnails under `projects/<id>/layouts/thumbnails/<slug>.png`.
- The project-local `.trash` collects unreferenced assets. The ProjectStatusBar shows its size, lets users prune it, and imports resurrect files from `.trash` when hashes match.
- Projects can be exported/imported as `.sq` archives (zip ohne `.trash`) via the status bar actions.
- Layout presets are defined in `src/slidequest/models/layouts.py`; each card in the Detail footer is built from these specs.

## Status & Navigation Surfaces

- **NavigationRail** (left, formerly SymbolView) switches between Layout-, Audio-, Notes- und File-Subapps. Currently only Layout toggles the Explorer/Detail panes; the other launchers are placeholders for upcoming subapps.
- **ProjectStatusBar** (top) shows logo + project title, project management actions (New/Open/Import/Export/Reveal/Prune) and a live indicator of how much disk space the project trash consumes.
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
