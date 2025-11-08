# SlideQuest Task Backlog

Use this file whenever a request is too large for a single prompt. Each top-level bullet should describe one high-level feature, followed by sub-bullets that can be completed in individual prompts.

- _Example_: Implement slide import pipeline
  - Parse PowerPoint metadata into intermediate objects
  - Map slide elements to PresentationWindow widgets
  - Add regression tests for parser edge cases

- Adopt MVVP architecture for SlideQuest
  - Define target module structure (models/viewmodels/views/services) and migrate layout + slide dataclasses
  - Extract LayoutPreview widgets and PresentationWindow into dedicated view modules
  - Introduce a MasterViewModel that mediates between storage and UI interactions
  - Update `app.py` / bootstrap to compose the new layers and adjust docs/tests accordingly

Append new tasks at the top so the latest priorities stay visible. Remove bullets once all subtasks are done or explicitly dropped.
