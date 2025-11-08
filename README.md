## SlideQuest (PySide6-Prototyp)

Dieses Verzeichnis enthält den neuen SlideQuest-Prototyp, der langfristig die `MTMT*`-Legacy-Apps ersetzt. Die UI basiert auf **PySide6**, Abhängigkeiten werden vollständig mit **uv** verwaltet.

> Dieses README ist die deutschsprachige Kurzfassung des SlideQuest-Handbuchs in `docs/Handbook.md` (Obsidian-Struktur). Beide Dokumente müssen nach jeder Prozessänderung aktualisiert werden.

### Handbuch-Highlights

- Bevorzuge einfache Lösungen, kleine Dateien und halte die kognitive Komplexität so gering wie möglich.
- Kläre Rückfragen, bevor du baust, sobald Anforderungen nicht eindeutig sind.
- Dokumentiere große Features in `Tasks.md`, zerlege sie in promptgerechte Schritte und arbeite sie iterativ ab.
- Halte `AGENTS.md` (KI-Anweisungen) und dieses README immer synchron mit dem Handbuch.
- Wenn Layoutbereiche zum Test eingefärbt werden sollen, nutze knallige, klar unterscheidbare Farben.
- Jede Komponente wird so gebaut, dass sie sich isoliert wiederverwenden lässt (saubere Eingaben, keine versteckten Seiteneffekte).

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
- `docs/Handbook.md` – kanonisches Handbuch (englisch, Obsidian-kompatibel).
- `Tasks.md` – Backlog für umfangreiche Aufgaben, aufgeteilt in promptfähige Teilaufgaben.
- `assets/` – Referenzmaterial (z. B. Layout-Skizzen).
- `MTMT*` – Legacy-Projekt (nur lesen, nicht verändern).

### Layout-Referenz

![MasterWindow Layout](assets/MasterWindow_GeneralLayout.png)

Die Abbildung zeigt die aktuelle Zwei-\*Drei-Teilung des MasterWindow (StatusBar, SymbolView, Explorer- und Detail-Bereiche mit ihren Subviews) und dient als visuelle Grundlage für weitere Anpassungen.
Zusätzliche Symbolleisten-Icons (Audio, Dateien, Fenster, Layouts) liegen als Bootstrap-SVGs unter `assets/icons/bootstrap/<kategorie>/` bereit.

### Nächste Schritte

Neue Module gehören nach `src/slidequest` (z. B. Slide-Parsing, Datenquellen, Layoutlogik). Der aktuelle Doppel-Fenster-Aufbau dient als Grundlage für weitere Features – ersetze die Platzhalter schrittweise durch die produktiven Komponenten.
