# Global Refactor Plan (Atlas)

## 1) Zielbild
- SlideQuest soll komplett Atlas-konform sein: modulare Architektur, sichere Services, konsistente UI-Controller, umfassende Tests & Telemetrie.
- Scope: alle Bereiche außerhalb der bereits überarbeiteten AI-Section (Explorer, Notes, Playlist, Presentation, Services).

## 2) Prioritäten & Wellen
1. **Explorer & MasterWindow**
   - Ziel: Explorer-Widgets, Buttons, Drag/Drop, CRUD, Statusbar vereinheitlichen.
   - Deliverables: ExplorerController, SlideItem-ViewModel, Tests für Reorder/CRUD.
2. **Playlist & Notes**
   - Ziel: PlaylistListWidget + NotesSection modularisieren, Tests für reorder & persistence.
3. **Services & Utilities**
   - Ziel: Storage, audio/Govee services, tokens – Audit & Refactor (Dependency injection, logging, tests).
4. **Presentation & Rendering**
   - Ziel: PresentationWindow modularisieren, Telemetrie (slide sync), Tests für preview/regenerate.
5. **Cross-Cutting**
   - Ziel: globale Telemetrie, Logging-Route, README/Liesmich, CI scripts.

## 3) Workflow pro Welle
- Markdown-Plan (z. B. `docs/ocs/explorer_refactor_plan.md`) mit Zielen, Risiken, Tasks.
- Code in kleinen, isolierten Schritten (Controller/Helper statt Mega-Views).
- Tests (Unit +, wo sinnvoll, Integration) – via `make test` (uv).
- Dokumentation (README/Liesmich/AGENTS) aktualisieren, Telemetrie konfigurieren.

## 4) Demokratischer Zeitplan (vorschlag)
- Welle 1: Explorer/MasterWindow (Buttons, Controller, Tests)
- Welle 2: Playlist/Notes
- Welle 3: Services
- Welle 4: Presentation
- Welle 5: Cross-cutting (Landing).

## 5) Nächste Aktion
- Start mit Welle 1: Explorer (Teil 1) – Detailplan erstellen, Controls implementieren, Tests.
