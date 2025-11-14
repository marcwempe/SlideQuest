# SlideQuest Task Backlog

Use this file whenever the user assigns multi-step work that cannot be finished within a single prompt. Each top-level bullet should describe a high-level feature or refactor, followed by sub-bullets that can be delivered independently.

_Template_
- Feature / Refactor name
  - Subtask 1
  - Subtask 2
  - ...

Append new tasks at the top so the most recent priorities stay visible. Remove bullets once all subtasks are complete or explicitly dropped.

- Seedream Prompt Workflow
  - Style-Prompt Drawer rechts vom Prompt einfügen, Inhalt projektspezifisch speichern und bei Generierung anhängen
  - Letzten Prompt je Slide sichern und beim Slide-Wechsel ins Eingabefeld zurückspielen
  - Galerie im Footer um Bild-Vorschau bei Klick und Kontextmenü-Löschen via Rechtsklick erweitern
- Govee Light Control Integration
  - Navigationsbutton inkl. Bootstrap-Icon hinzufügen & API-Key-Check aus .env implementieren
  - LightControlView (Header/Main/Footer) erstellen, Geräte synchronisieren und als Header-Icons listen
  - Fehlenden API-Key via Dialog nachfordern und Geräteverwaltung laut docs/assets/thirdparty/govee vorbereiten
- Replicate Seedance Integration
  - KI-Unterstützungsbutton in Navigation inkl. Bootstrap-Icon & API-Key-Handling (.env oder Dialog)
  - Seedance-Steuerung im Detailbereich basierend auf docs/assets/thirdparty/replicate (Prompts, Einstellungen, Start/Status)
  - Storage-Bereich + rechter Drawer für generierte Bilder inkl. Drag&Drop in Layoutflächen
  - Bild-zu-Bild-Unterstützung inkl. Referenzbild-Verwaltung und Seedream Parameterübergabe
- Token-basierte Layout-Dekoration
  - Token-Leiste im Layout-Header einbauen (Bild + Overlay + Opacity-Map pro Token, Drag&Drop zum Befüllen)
  - Tokens per Drag&Drop auf Preview/Presentation platzieren, inkl. persistenter Position/Skalierung pro Slide
  - Rechte-Maus-Menü für Overlay-Auswahl/Löschen implementieren; Overlay = Bild + Alpha-Maske
  - Transformationswerkzeuge: Verschieben, skalieren mit Rastung (0.5x Schritte, Alt = frei, Shift = vom Mittelpunkt)
- Scope-Aufteilung Audio/Layout vs. Slides
  - Audio-Header + Layout-Header bleiben Project-Scope (ProjectStorageService)
  - Soundboard-Button-Zustände (aktiv/Loop) slideweise abspeichern
  - Token-Platzierung/Größe/Position je Slide speichern
