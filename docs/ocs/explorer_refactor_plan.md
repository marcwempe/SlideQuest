# Explorer Refactor Plan (Welle 1)

## Ziele
- ExplorerSectionMixin entschlacken (Controller für CRUD/Selection & UI-Widget).
- SlideListWidget verallgemeinern (Status-Updates, Buttons, Filter).
- Tests für Slide-Reorder (Buttons + Drag) und CRUD.

## Aufgaben
1. ExplorerController definieren (zuständig für ViewModel-Calls: create/edit/delete/select/reorder). ✅
2. SlideListItem-Widget extrahieren (eigene Klasse unter `views/widgets`), Testerstellung einfacher.
3. Unit-Tests: Controller, Buttons (Qt-Test via pytest-qt), Reorder + CRUD Cases (Teil-1 erledigt für Controller).
4. Dokumentation + Plan-Updates.

## Risiken
- MasterWindow initialisiert ExplorerSectionMixin früh; neue Komponenten müssen lazy sein.
- Tests brauchen Dummy-ViewModel/Slides.
- UI-Styling darf nicht brechen (CSS anpassen).

## Erfolgskriterien
- ExplorerSectionMixin < 800 Zeilen, Controller + Widget ausgelagert.
- Reorder-Buttons + DragWorks + Tests.
- Keine Regression (make test grün).
