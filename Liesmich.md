# SlideQuest – Liesmich

SlideQuest ist ein PySide6-Prototyp für das Erstellen und Präsentieren von Multimediainhalten. Zwei Fenster arbeiten zusammen: Das `MasterWindow` dient als Steuerzentrale, das `PresentationWindow` zeigt das Ergebnis. Sämtlicher Code wird von OpenAI Codex erzeugt und steht unter der GNU GPL v3.

## Werkzeuge & Befehle

| Aufgabe | Befehl |
| --- | --- |
| Abhängigkeiten installieren | `uv sync` |
| App starten | `uv run slidequest` / `make run` |
| Hot Reload | `uv run slidequest-dev` / `make dev` |
| Paket hinzufügen | `uv add <paket>` |

Weitere Hinweise:

- Python 3.12+, `uv` als Paketmanager, `watchfiles` für Reload.
- Für Suchen `rg` nutzen; Dateien nur dann mit Unicode erweitern, wenn es bereits nötig ist.

## Projektstruktur

- `src/slidequest/app.py` – schlanker Einstieg, der Master- und Präsentationsfenster startet.
- `src/slidequest/models/…` – Layout- und Slide-Daten.
- `src/slidequest/viewmodels/…` – ViewModels (z. B. `MasterViewModel`).
- `src/slidequest/services/storage.py` – JSON-Speicherung.
- `src/slidequest/views/master_window.py` – komplette `MasterWindow`-Logik inkl. Panels.
- `src/slidequest/views/presentation_window.py` – separates Präsentationsfenster.
- `src/slidequest/views/widgets/layout_preview.py` – Layout-Canvas + Karten.
- `src/slidequest/utils/media.py` – Helfer für Slugs und Medienpfade.
- `assets/` – Referenzgrafiken und automatisch erzeugte Thumbnails.
- `docs/assets/LayoutViewScreenshot.png` – aktueller Screenshot für die Doku.
- `AGENTS.md` – operative Vorgaben für KI-Agenten.

![Layout-Ansicht](docs/assets/LayoutViewScreenshot.png)

## UI-Highlights

- **SymbolView**: Vertikale Navigationsleiste mit Launchern für Layout, Audio, Notes und Files. Aktive Buttons erhalten eine farbige Linksmarkierung.
- **StatusBar**: Artwork + Titel, Audio-Seekbar (zentriert) und Transport-/Volume-Steuerung auf der rechten Seite. Icons folgen dem Betriebssystem-Thema (hell in Dark Mode, dunkel in Light Mode).
- **Explorer/Detail**: ExplorerHeader mit Suche + Filter, ExplorerFooter mit CRUD. DetailMain zeigt die Layout-Vorschau; DetailFooter enthält die horizontale Layout-Auswahl.
- **PresentationWindow**: Wird über den unteren SymbolView-Button geöffnet; es darf nur eine Instanz gleichzeitig existieren.

## Datenmodell

Slides liegen in `data/slides.json`. Jede Folie enthält Titel, Untertitel, Gruppe sowie einen `layout`-Block (`active_layout`, `thumbnail_url`, `content`). `content[i]` adressiert den Bereich `#i+1`. Layoutwechsel löschen keine übrigen Bilder; sie werden automatisch wieder sichtbar, sobald ein Layout genügend Plätze bietet. Jede Änderung an Layout oder Dropped Media löst ein erneutes Thumbnail-Rendering (`assets/thumbnails/<slug>.png`) aus.

## Lokalisierung & Zugänglichkeit

- Alle Steuerelemente besitzen Tooltips mit ihrer eindeutigen ID.
- Strings müssen über die vorgesehenen i18n-Helfer laufen (aktuell in `ui/constants.py` vorgesehen).
- Dark-/Light-Mode wird automatisch erkannt; Icons werden entsprechend neu eingefärbt.

## Herkunft & Lizenz

- Entwickler: OpenAI Codex (vollständige Automatisierung).
- Lizenz: **GNU General Public License v3.0**, siehe `LICENSE`.
- Beiträge müssen dieselbe Lizenz verwenden, Lokalisierungsregeln beachten und Änderungen sowohl in README als auch in Liesmich dokumentieren.

## Git-Workflow

1. **Synchronisieren & Branch anlegen** – `main` aktualisieren (`git pull origin main`) und mit `git checkout -b feature/<thema>` auf einen Feature-Branch wechseln. Keine direkten Commits auf `main`.
2. **Kleine Pakete** – Änderungen kleinteilig halten, Docs/i18n sofort mitziehen und umfangreiche Arbeiten rechtzeitig abstimmen.
3. **Lokal testen** – `uv run slidequest` bzw. `make dev` ausführen; bei Bedarf zusätzliche Checks ergänzen.
4. **Selektiv stagen** – Mit `git status` und `git add -p` nur gewünschte Dateien übernehmen; generierte Artefakte (Thumbnails etc.) bewusst prüfen.
5. **Commit-Nachricht** – Präsens + kurzer Kontext („Verbessere Layout-Auswahl“). Auf zugehörige Tasks verweisen, falls vorhanden.
6. **Push & Review** – `git push -u origin feature/<thema>` und PR gegen `main` eröffnen; Dokumentationsänderungen kurz erwähnen.
7. **Merge & Aufräumen** – Nach Review squashen/fast-forwarden, den Branch lokal und remote löschen und die Arbeitskopie erneut synchronisieren.
