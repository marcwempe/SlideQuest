# Style & Prompt Binding Audit

## 1. High-Level-Verständnis
- Goal: evaluate existing Prompt/Style bindings in `AISectionMixin` (TextBinding), assess responsibilities, risks, and whether additional controllers/splits are needed.
- Risks: TextBinding currently handles raw QTextEdit interactions, but AISection still owns a multitude of responsibilities (UI wiring, ViewModel access, Reference imports). Need to ensure binding logic stays cohesive, extendable, and testable.

## 2. Domänenanalyse
- Domain objects: `TextBinding` (editor binding), `_viewmodel` (slide + style prompt state), `_ai_style_toggle` (drawer state), `_ai_prompt_input`/`_ai_style_input`.
- Current responsibilities:
  - TextBinding reads/writes values + triggers optional `on_change` callback.
  - AISection ensures toggle state matches binding content (style drawer auto-collapse).
- Potential improvement: dedicated controller for style/prompt state to reduce direct ViewModel coupling within mixin.

## 3. Architekturbeobachtung
- Current architecture: AISectionMixin (UI adapter) → TextBinding (helper) → ViewModel (state). Hex-like separation is ok, but AISection still orchestrates state toggles.
- Candidate split: create `StylePromptController` (managing binding, toggle state, viewmodel interactions). Would isolate `_handle_style_text_changed` logic + make integration tests easier.

## 4. Designentscheidungen
- Option A: keep TextBinding + add a small controller struct. Advantage: minimal change, targeted responsibilities. Disadvantage: another small class but reduces AISection bloat.
- Option B: full MVVM controller (overkill). Plan chooses Option A (lightweight controller) if we proceed.

## 5. Technische Umsetzung (next steps)
- Introduce `StylePromptController` (module `ai_style_controller.py`). Responsibilities: init binding, sync to viewmodel, handle toggle suggestions.
- AISectionMixin uses controller instead of direct TextBinding references.
- Reuse existing binding tests, add new unit tests for controller.

## 6. Tests & Edge Cases
- Unit: `test_style_prompt_controller.py` verifying sync, toggle recommendations, viewmodel interactions.
- Integration: existing AISection tests reuse controller automatically.

## 7. Debuggingstrategie
- If issues arise, check binding state vs. viewmodel output; controller isolates logic, so hooking logs easier.

## 8. Qualität & DevOps
- Controller reduces complexity of AISection, improves testability. No build changes needed.

## 9. Evolution & Wartung
- Future features (style presets, cross-slide overrides) can live in controller, not UI mixin.

## 10. Next Actions
1. Implement `StylePromptController` (encapsulate TextBinding + toggle logic).
2. Update AISectionMixin to use controller.
3. Add unit tests for controller.
