# SlideQuest - Liesmich

SlideQuest ist ein PySide6-Prototyp für das Erstellen und Präsentieren von Multimediainhalten. Zwei Fenster arbeiten zusammen: Das `MasterWindow` dient als Steuerzentrale, das `PresentationWindow` zeigt das Ergebnis. Sämtlicher Code wird von OpenAI Codex erzeugt und steht unter der GNU GPL v3.

## Werkzeuge & Befehle

| Aufgabe | Befehl |
| --- | --- |
| Abhängigkeiten installieren | `uv sync` |
| App starten | `uv run slidequest` / `make run` |
| Hot Reload | `uv run slidequest-dev` / `make dev` |
| Paket hinzufügen | `uv add <paket>` |
| Tests | `make test` (PySide6/pytest im Offscreen-Modus) |

Weitere Hinweise:

- Python 3.12+, `uv` als Paketmanager, `watchfiles` für Reload.
- Für Suchen `rg` nutzen; Dateien nur dann mit Unicode erweitern, wenn es bereits nötig ist.

## Projektstruktur

- `src/slidequest/app.py` - schlanker Einstieg, der Master- und Präsentationsfenster startet.
- `src/slidequest/models/...` - Layout- und Slide-Daten.
- `src/slidequest/viewmodels/...` - ViewModels (z. B. `MasterViewModel`).
- `src/slidequest/services/storage.py` - Projektspeicher + JSON-Serialisierung.
- `src/slidequest/services/project_service.py` - AppData-Ordner, Asset-Import (Hash/UUID) und Papierkorb.
- `src/slidequest/views/master_window.py` - komplette `MasterWindow`-Logik inkl. Panels.
- `src/slidequest/views/presentation_window.py` - separates Präsentationsfenster.
- `src/slidequest/views/widgets/layout_preview.py` - Layout-Canvas + Karten.
- `src/slidequest/views/widgets/common.py` - gemeinsame UI-Helfer (FlowLayout, Icon-Buttons).
- `src/slidequest/utils/media.py` - Helfer für Slugs und Medienpfade.
- `assets/` - Referenzgrafiken und automatisch erzeugte Thumbnails.
- `docs/assets/LayoutViewScreenshot.png` - aktueller Screenshot für die Doku.
- `AGENTS.md` - operative Vorgaben für KI-Agenten.

![Layout-Ansicht](docs/assets/LayoutViewScreenshot.png)

## Architektur

- `slidequest/app.py` startet die QApplication, erzeugt `MasterWindow` + `PresentationWindow` und verknüpft beide.
- `MasterWindow` (`views/master_window.py`) baut die Oberfläche, lagert aber alle Zustandsänderungen an das `MasterViewModel` aus.
- `MasterViewModel` (`viewmodels/master.py`) nutzt `SlideStorage` plus `ProjectStorageService`. Jede Folie lebt in einem Projektordner unter `~/Library/Application Support/SlideQuest/projects/<id>` (bzw. `%APPDATA%\\SlideQuest\\projects\\<id>`), wo `project.json` Slides, Asset-Hash-Map und Papierkorb verwaltet.
- `PresentationWindow` zeigt die aktuelle Folie und liefert die Quelle für Thumbnails; es existiert immer genau eine Instanz.
- Wiederverwendbare Hilfen (z. B. `utils/media.py`, `views/widgets/common.py`) bündeln Slug-/Pfad-Logik sowie FlowLayout/Icon-Buttons.

## UI-Highlights

- **NavigationRail**: Startpunkt für Layout-, Audio-, Notes- und File-Ansichten (derzeit nur Layout aktiv); aktive Buttons behalten die Linksmarkierung.
- **ProjectStatusBar**: Zeigt Logo + Projektnamen, Projektaktionen (Neu, Öffnen, Import, Export, Ordner öffnen, Papierkorb leeren) sowie den aktuellen Papierkorb-Füllstand.
- **Explorer/Detail**: ExplorerHeader mit Suche + Filter, ExplorerFooter mit CRUD. DetailMain zeigt die Layout-Vorschau; DetailFooter enthält die horizontale Layout-Auswahl.
- **PresentationWindow**: Wird über den unteren SymbolView-Button geöffnet; es darf nur eine Instanz gleichzeitig existieren.

## Datenmodell

Slides liegen pro Projekt in `project.json`. Neben einer `slides`-Liste gibt es ein `files`-Mapping, das alle importierten Dateien (layouts/audio/notes) über Hash/UUID referenziert. `content[i]` adressiert weiterhin den Bereich `#i+1`; Layout-Beschreibungen mit `#` definieren feste Zuordnungen. `MasterViewModel` importiert neue Medien automatisch in den Projektordner, synchronisiert `content`/`images` und rendert Thumbnails nach `projects/<id>/layouts/thumbnails/<slug>.png`. Unbenutzte Dateien wandern in `.trash`, lassen sich über die ProjectStatusBar leeren und werden bei passenden Hashes automatisch wiederhergestellt. Projekte können als `.sq` exportiert/importiert (Zip ohne `.trash`) werden.

## Lokalisierung & Zugänglichkeit

- Alle Steuerelemente besitzen Tooltips mit ihrer eindeutigen ID.
- Die Texte sind aktuell hart verdrahtet. Halte sie kurz/sachlich, damit eine spätere Lokalisierung (z. B. automatische deutsche UI bei deutscher OS-Sprache) ohne großen Umbau möglich bleibt.
- Dark-/Light-Mode wird automatisch erkannt; Icons werden entsprechend neu eingefärbt.

## Herkunft & Lizenz

- Entwickler: OpenAI Codex (vollständige Automatisierung).
- Lizenz: **GNU General Public License v3.0**, siehe `LICENSE`.
- Beiträge müssen dieselbe Lizenz verwenden, Lokalisierungsregeln beachten und Änderungen sowohl in README als auch in Liesmich dokumentieren.

## Git-Workflow

1. **Synchronisieren & Branch anlegen** - `main` aktualisieren (`git pull origin main`) und mit `git checkout -b feature/<thema>` auf einen Feature-Branch wechseln. Keine direkten Commits auf `main`.
2. **Kleine Pakete** - Änderungen kleinteilig halten, Docs/i18n sofort mitziehen und umfangreiche Arbeiten rechtzeitig abstimmen.
3. **Lokal testen** - `uv run slidequest` bzw. `make dev` ausführen; bei Bedarf zusätzliche Checks ergänzen.
4. **Selektiv stagen** - Mit `git status` und `git add -p` nur gewünschte Dateien übernehmen; generierte Artefakte (Thumbnails etc.) bewusst prüfen.
5. **Commit-Nachricht** - Präsens + kurzer Kontext ("Verbessere Layout-Auswahl"). Auf zugehörige Tasks verweisen, falls vorhanden.
6. **Push & Review** - `git push -u origin feature/<thema>` und PR gegen `main` eröffnen; Dokumentationsänderungen kurz erwähnen.
7. **Merge & Aufräumen** - Nach Review squashen/fast-forwarden, den Branch lokal und remote löschen und die Arbeitskopie erneut synchronisieren.
