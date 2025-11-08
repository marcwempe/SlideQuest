## SlideQuest (PySide6-Prototyp)

Dieses Verzeichnis enthält den neuen SlideQuest-Prototyp, der langfristig die `MTMT*`-Legacy-Apps ersetzt. Die UI basiert auf **PySide6**, Abhängigkeiten werden vollständig mit **uv** verwaltet.

> Dieses README ist die deutschsprachige Kurzfassung des SlideQuest-Handbuchs in `docs/Handbuch.md` (Obsidian-Struktur). Beide Dokumente müssen nach jeder Prozessänderung aktualisiert werden.

### Handbuch-Highlights

- Bevorzuge einfache Lösungen, kleine Dateien und halte die kognitive Komplexität so gering wie möglich.
- Kläre Rückfragen, bevor du baust, sobald Anforderungen nicht eindeutig sind.
- Dokumentiere große Features in `Tasks.md`, zerlege sie in promptgerechte Schritte und arbeite sie iterativ ab.
- Halte `AGENTS.md` (KI-Anweisungen) und dieses README immer synchron mit dem Handbuch.
- Wenn Layoutbereiche zum Test eingefärbt werden sollen, nutze knallige, klar unterscheidbare Farben.
- Jede Komponente wird so gebaut, dass sie sich isoliert wiederverwenden lässt (saubere Eingaben, keine versteckten Seiteneffekte).
- Sämtliche Texte müssen i18n-fähig sein; die gewählte Sprache richtet sich nach der Systemsprache (UI lokalisiert sich automatisch).

### Systemvoraussetzungen

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (global installiert, z. B. per `pip install uv`)

### Einrichtung

```bash
uv sync
```

Damit wird ein lokales `.venv` erzeugt und alle Abhängigkeiten installiert.

### Tägliche Befehle

| Aufgabe | Befehl |
| --- | --- |
| GUI einmal starten | `uv run slidequest` / `make run` |
| Hot-Reload starten | `uv run slidequest-dev` / `make dev` |
| Neue Abhängigkeit hinzufügen | `uv add <paket>` |

Der Dev-Watcher nutzt `watchfiles`, um die GUI automatisch neu zu starten, sobald sich Dateien in `src/slidequest` oder `pyproject.toml` ändern. Die `make`-Targets sind Kurzformen für die entsprechenden uv-Aufrufe (`make run`, `make dev`, `make sync`).

### Projektstruktur

- `src/slidequest/app.py` – Einstiegspunkt sowie Verkabelung von Master- und Presentation-Window.
- `src/slidequest/dev.py` – Watchfiles-basierter Dev-Loop.
- `AGENTS.md` – Instruktionen für KI-Agenten (englisch, technisch).
- `docs/Handbuch.md` – kanonisches Handbuch (deutsch, Obsidian-kompatibel).
- `Tasks.md` – Backlog für umfangreiche Aufgaben, aufgeteilt in promptfähige Teilaufgaben.
- `assets/` – Referenzmaterial (z. B. Layout-Skizzen); `assets/thumbnails/` enthält generierte Layout-Vorschauen.
- `data/slides.json` – Persistente Slide-Liste inkl. Layout-, Audio- und Notizzuweisungen.
- `MTMT*` – Legacy-Projekt (nur lesen, nicht verändern).

### Layout-Referenz

![MasterWindow Layout](assets/MasterWindow_GeneralLayout.png)

Die Abbildung zeigt die aktuelle Zwei-\*Drei-Teilung des MasterWindow (StatusBar, SymbolView, Explorer- und Detail-Bereiche mit ihren Subviews) und dient als visuelle Grundlage für weitere Anpassungen.

![MasterWindow Steuerzentrale](assets/MasterWindow_ZentraleSteuerelemente.png)

Die zweite Grafik zoomt auf die Statusbar und die SymbolView: Sie zeigt Navigations-Buttons (Layout, Audio, Note, File) und die Audio-Steuerung (Seekbar, Transport, Volume) als verbindliche Referenz für Beschriftungen und Interaktion.
Im ExplorerHeaderView sitzen Suchfeld und Filter-Button (Bootstrap-Icons `search`/`filter`), während der ExplorerFooterView derzeit `ExplorerCreateButton` und `ExplorerDeleteButton` für CRUD-Fälle anbietet (weitere Aktionen folgen bei Bedarf).
Zusätzliche Symbolleisten-Icons (Audio, Dateien, Fenster, Layouts) liegen als Bootstrap-SVGs unter `assets/icons/bootstrap/<kategorie>/` bereit. Die SymbolView fungiert als Navigation: Jeder Button öffnet eine Sub-Anwendung im Explorer- und Detailbereich. Der `FileExplorerLauncher` lädt die programmeigene Asset-Library für Bilder, Videos, Audios und Markdown-Dateien; `NoteExplorerLauncher`, `AudioExplorerLauncher` und `LayoutExplorerLauncher` folgen demselben Muster für weitere Spezialbereiche.

![MasterWindow Steuerzentrale mit Explorer](assets/MasterWinder_ZentraleSteuerelemente_MitExplorer.png)

Die dritte Grafik kombiniert SymbolView, Statusbar und Explorer-Header/-Footer als globale Steuerzentrale, unabhängig von der Sub-App.

### Slides & Datenmodell

- `ExplorerMainView` listet jetzt Slides, nicht mehr Layoutvorlagen. Angezeigt werden Titel, Untertitel, Gruppe und ein Thumbnail des letzten gespeicherten Layout-Arrangements.
- Die Daten stammen aus `data/slides.json` und folgen exakt der im Handbuch dokumentierten Struktur (Layout-Block mit `active_layout`, `thumbnail_url`, `content`, dazu Audio-Playlists und Notiz-Links). Die Einträge unter `content` gehören zum Slide selbst – Index `i` repräsentiert Layoutbereich `#i`. Beim Layoutwechsel wird nur die Darstellung, nicht der Bestand, verändert.
- Die `LayoutSelectionList` enthält sämtliche Templates (`LAYOUT_ITEMS`). Ein Wechsel setzt `layout.active_layout`, verwirft nicht mehr passende Drop-Zuweisungen und erzeugt direkt ein neues Thumbnail, indem das `PresentationWindow` off-screen gerendert und in `assets/thumbnails/<slug>.png` gespeichert wird.
- Gleiches gilt beim Ersetzen einzelner Bereiche per Drag & Drop: Die Bildpfade werden relativ zum Projekt gespeichert, der neue Zustand persistent aktualisiert und sofort als Thumbnail angezeigt.

### Nächste Schritte

Neue Module gehören nach `src/slidequest` (z. B. Slide-Parsing, Datenquellen, Layoutlogik). Der aktuelle Doppel-Fenster-Aufbau dient als Grundlage für weitere Features – ersetze die Platzhalter schrittweise durch die produktiven Komponenten.
