# Explorer Reorder Controls Plan

## Ziel
- SlideExplorer-Liste erhält direkte Auf/Ab-Schaltflächen je Item.
- UX soll klarer sein (Icons statt Text, Buttons deaktivieren, wenn Verschiebung nicht möglich).
- Autoscroll verhalten bleibt unverändert (bereits refaktoriert).

## Aufgaben
1. Buttons im Explorer-Item visuell verfeinern (Icons `move_up/move_down`, Tooltips, feste Größe).
2. Buttons deaktivieren, wenn das Item bereits ganz oben/unten ist (`_update_slide_item_states`).
3. Sicherstellen, dass Buttons nach Rebuild/Filter korrekt aktualisiert werden.
4. PyCompile/Testlauf zur Sicherung der Änderung.

## Risiken
- Widgets werden beim Rebuild neu erzeugt; Aktivierungszustand muss bei jedem `_update_slide_item_states` gesetzt werden.
- Lambdas für `_move_slide` dürfen nicht mehrere `slide`-Referenzen teilen -> via default arg lösen.
- Keine Regression für Drag&Drop.

## Erfolgskriterien
- Icons + Größe konsistent.
- Buttons disabled an den Grenzen.
- `make test` bleibt grün.
