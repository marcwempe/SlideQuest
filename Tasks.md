# SlideQuest Task Backlog

Use this file whenever the user assigns multi-step work that cannot be finished within a single prompt. Each top-level bullet should describe a high-level feature or refactor, followed by sub-bullets that can be delivered independently.

_Template_
- Feature / Refactor name
  - Subtask 1
  - Subtask 2
  - ...

Append new tasks at the top so the most recent priorities stay visible. Remove bullets once all subtasks are complete or explicitly dropped.

- Token-basierte Layout-Dekoration
  - Token-Leiste im Layout-Header einbauen (Bild + Overlay + Opacity-Map pro Token, Drag&Drop zum Befüllen)
  - Tokens per Drag&Drop auf Preview/Presentation platzieren, inkl. persistenter Position/Skalierung pro Slide
  - Rechte-Maus-Menü für Overlay-Auswahl/Löschen implementieren; Overlay = Bild + Alpha-Maske
  - Transformationswerkzeuge: Verschieben, skalieren mit Rastung (0.5x Schritte, Alt = frei, Shift = vom Mittelpunkt)
- Scope-Aufteilung Audio/Layout vs. Slides
  - Audio-Header + Layout-Header bleiben Project-Scope (ProjectStorageService)
  - Soundboard-Button-Zustände (aktiv/Loop) slideweise abspeichern
  - Token-Platzierung/Größe/Position je Slide speichern
