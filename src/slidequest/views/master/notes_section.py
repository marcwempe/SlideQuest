from __future__ import annotations

from datetime import datetime
from pathlib import Path
import tempfile

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QTextBlockFormat, QTextCharFormat, QTextCursor, QTextListFormat, QTextFormat
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QStackedWidget,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

try:  # pragma: no cover - optional dependency
    from PySide6.QtPdf import QPdfDocument  # type: ignore
    from PySide6.QtPdfWidgets import QPdfView  # type: ignore
except Exception:  # pragma: no cover - fallback when QtPdf is missing
    QPdfDocument = None
    QPdfView = None

from slidequest.services.storage import DATA_DIR
from slidequest.ui.constants import ACTION_ICONS, DETAIL_FOOTER_HEIGHT, DETAIL_HEADER_HEIGHT
from slidequest.utils.media import resolve_media_path
from slidequest.views.widgets.document_list import DocumentListWidget


class NotesSectionMixin:
    """Mix-in hosting the notes detail view with markdown/PDF rendering."""

    MARKDOWN_EXTENSIONS = {".md", ".markdown", ".mdown", ".mkd", ".txt"}
    PDF_EXTENSIONS = {".pdf"}

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[misc]
        self._note_document_list: DocumentListWidget | None = None
        self._note_renderer_stack: QStackedWidget | None = None
        self._note_editor: QTextEdit | None = None
        self._note_pdf_view: QPdfView | QLabel | None = None
        self._note_pdf_document: QPdfDocument | None = QPdfDocument() if QPdfDocument else None
        self._note_placeholder_label: QLabel | None = None
        self._note_error_label: QLabel | None = None
        self._note_toolbar_buttons: dict[str, QToolButton] = {}
        self._note_active_file_label: QLabel | None = None
        self._note_current_path: str | None = None
        self._note_current_type: str = ""
        self._note_dirty = False
        self._note_default_font_size = 12.0

    # ------------------------------------------------------------------ #
    # Construction
    # ------------------------------------------------------------------ #
    def _build_notes_detail_view(self, parent: QWidget | None = None) -> QWidget:
        view = QWidget(parent)
        view.setObjectName("NotesDetailView")
        layout = QVBoxLayout(view)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame(view)
        header.setObjectName("NotesDetailHeader")
        header.setFixedHeight(DETAIL_HEADER_HEIGHT)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 6, 12, 6)
        header_layout.setSpacing(8)
        self._build_notes_header_controls(header_layout)

        renderer_stack = QStackedWidget(view)
        renderer_stack.setObjectName("NotesRendererStack")
        self._note_renderer_stack = renderer_stack

        placeholder = QLabel("Noch kein Dokument ausgewählt.", renderer_stack)
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setObjectName("NotesPlaceholderLabel")
        renderer_stack.addWidget(placeholder)
        self._note_placeholder_label = placeholder

        editor = QTextEdit(renderer_stack)
        editor.setObjectName("NotesMarkdownEditor")
        editor.setAcceptRichText(True)
        editor.setPlaceholderText("Markdown-Inhalt bearbeiten …")
        editor.textChanged.connect(self._handle_note_text_changed)
        renderer_stack.addWidget(editor)
        self._note_editor = editor
        self._note_default_font_size = self._resolve_default_font_size(editor)

        if QPdfView is not None and self._note_pdf_document is not None:
            pdf_view = QPdfView(renderer_stack)
            pdf_view.setObjectName("NotesPdfViewer")
            pdf_view.setZoomMode(QPdfView.ZoomMode.FitInView)
            pdf_view.setDocument(self._note_pdf_document)
        else:
            pdf_view = QLabel("PDF-Vorschau ist auf diesem System nicht verfügbar.", renderer_stack)
            pdf_view.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pdf_view.setWordWrap(True)
        renderer_stack.addWidget(pdf_view)
        self._note_pdf_view = pdf_view

        error_label = QLabel("Dokument konnte nicht geladen werden.", renderer_stack)
        error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_label.setWordWrap(True)
        error_label.setObjectName("NotesErrorLabel")
        renderer_stack.addWidget(error_label)
        self._note_error_label = error_label

        footer = QFrame(view)
        footer.setObjectName("NotesDetailFooter")
        footer.setFixedHeight(DETAIL_FOOTER_HEIGHT + 20)
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(12, 8, 12, 12)
        footer_layout.setSpacing(4)

        doc_list = DocumentListWidget(footer)
        doc_list.setFixedHeight(DETAIL_FOOTER_HEIGHT - 12)
        doc_list.filesDropped.connect(self._handle_note_files_dropped)
        doc_list.currentRowChanged.connect(self._handle_note_selection_changed)
        footer_layout.addWidget(doc_list)
        self._note_document_list = doc_list

        layout.addWidget(header)
        layout.addWidget(renderer_stack, 1)
        layout.addWidget(footer)

        self._populate_note_documents()
        return view

    def _build_notes_header_controls(self, layout: QHBoxLayout) -> None:
        new_button = self._create_icon_button(
            layout.parentWidget(),  # type: ignore[arg-type]
            "NotesNewDocumentButton",
            ACTION_ICONS["create"],
            "Neues Markdown-Dokument erstellen",
        )
        new_button.clicked.connect(self._handle_note_new_document)
        self._note_toolbar_buttons["new"] = new_button
        layout.addWidget(new_button)

        save_button = self._create_icon_button(
            layout.parentWidget(),  # type: ignore[arg-type]
            "NotesSaveDocumentButton",
            ACTION_ICONS["edit"],
            "Dokument speichern",
        )
        save_button.clicked.connect(self._handle_note_save_requested)
        save_button.setEnabled(False)
        self._note_toolbar_buttons["save"] = save_button
        layout.addWidget(save_button)

        layout.addSpacing(12)
        self._note_toolbar_buttons.update(
            self._create_text_format_buttons(layout)
        )

        layout.addStretch(1)

    def _create_text_format_buttons(self, layout: QHBoxLayout) -> dict[str, QToolButton]:
        buttons: dict[str, QToolButton] = {}
        parent = layout.parentWidget()
        specs = [
            ("clear", ACTION_ICONS["clear"], "Formatierung entfernen", self._clear_formatting),
            ("heading1", ACTION_ICONS["heading_1"], "Überschrift H1", lambda: self._apply_heading(1)),
            ("heading2", ACTION_ICONS["heading_2"], "Überschrift H2", lambda: self._apply_heading(2)),
            ("heading3", ACTION_ICONS["heading_3"], "Überschrift H3", lambda: self._apply_heading(3)),
            ("bold", ACTION_ICONS["text_bold"], "Fett formatieren", lambda: self._toggle_text_format("bold")),
            ("italic", ACTION_ICONS["text_italic"], "Kursiv formatieren", lambda: self._toggle_text_format("italic")),
            ("underline", ACTION_ICONS["text_underline"], "Unterstreichen", lambda: self._toggle_text_format("underline")),
            ("strike", ACTION_ICONS["text_strike"], "Durchstreichen", lambda: self._toggle_text_format("strike")),
            ("code", ACTION_ICONS["code"], "Code-Format anwenden", self._toggle_code_format),
            ("quote", ACTION_ICONS["quote"], "Zitatblock einfügen", self._toggle_block_quote),
            ("bullet", ACTION_ICONS["list_bullet"], "Aufzählung einfügen", lambda: self._toggle_list(QTextListFormat.Style.ListDisc)),
            ("number", ACTION_ICONS["list_number"], "Nummerierte Liste einfügen", lambda: self._toggle_list(QTextListFormat.Style.ListDecimal)),
        ]
        for key, icon, tooltip, handler in specs:
            button = self._create_icon_button(
                parent,
                f"NotesToolbar{key.capitalize()}Button",
                icon,
                tooltip,
            )
            button.clicked.connect(handler)
            layout.addWidget(button)
            buttons[key] = button
        for button in buttons.values():
            button.setEnabled(False)
        return buttons

    # ------------------------------------------------------------------ #
    # Population + state
    # ------------------------------------------------------------------ #
    def _populate_note_documents(self, select_path: str | None = None) -> None:
        if self._note_document_list is None:
            return
        self._commit_note_changes_if_needed()
        documents = self._viewmodel.note_documents()
        current_selection = select_path or self._note_current_path
        self._note_document_list.blockSignals(True)
        self._note_document_list.clear()
        for index, path in enumerate(documents):
            name = Path(path).name or f"Notiz {index + 1}"
            item = QListWidgetItem(name, self._note_document_list)
            item.setToolTip(path)
            item.setData(Qt.ItemDataRole.UserRole, path)
            self._note_document_list.addItem(item)
            if path == current_selection:
                self._note_document_list.setCurrentItem(item)
        self._note_document_list.blockSignals(False)
        if documents:
            if current_selection and current_selection in documents:
                self._load_note_document(current_selection)
            else:
                self._note_document_list.setCurrentRow(0)
                self._load_note_document(documents[0])
        else:
            self._note_current_path = None
            self._note_current_type = ""
            self._show_note_placeholder("Noch kein Dokument vorhanden.")

    def _handle_note_files_dropped(self, paths: list[str]) -> None:
        if not paths:
            return
        supported = [path for path in paths if self._is_supported_document(path)]
        if not supported:
            return
        added = self._viewmodel.add_note_documents(supported)
        if added:
            self._populate_note_documents(select_path=added[-1])

    def _handle_note_selection_changed(self, row: int) -> None:
        if self._note_document_list is None:
            return
        if not self._commit_note_changes_if_needed():
            pass
        item = self._note_document_list.item(row)
        if item is None:
            self._note_current_path = None
            self._note_current_type = ""
            self._show_note_placeholder("Noch kein Dokument ausgewählt.")
            return
        path = item.data(Qt.ItemDataRole.UserRole)
        if not path:
            return
        self._load_note_document(str(path))

    def _load_note_document(self, path: str) -> None:
        renderer = self._note_renderer_stack
        if renderer is None:
            return
        absolute = self._resolve_note_path(path)
        if not absolute.exists():
            self._show_note_error(f"Datei nicht gefunden:\n{absolute}")
            return
        suffix = absolute.suffix.lower()
        self._note_current_path = path
        if suffix in self.MARKDOWN_EXTENSIONS:
            self._display_markdown_document(absolute)
        elif suffix in self.PDF_EXTENSIONS:
            self._display_pdf_document(absolute)
        else:
            self._show_note_error(f"Der Dateityp {suffix or 'unbekannt'} wird nicht unterstützt.")

    def _display_markdown_document(self, absolute: Path) -> None:
        if self._note_editor is None or self._note_renderer_stack is None:
            return
        try:
            content = absolute.read_text(encoding="utf-8")
        except OSError as exc:
            self._show_note_error(f"Dokument konnte nicht gelesen werden:\n{exc}")
            return
        self._note_current_type = "markdown"
        self._note_editor.blockSignals(True)
        self._note_editor.setMarkdown(content)
        self._note_editor.moveCursor(QTextCursor.MoveOperation.Start)
        self._note_editor.blockSignals(False)
        self._note_renderer_stack.setCurrentWidget(self._note_editor)
        self._note_dirty = False
        self._update_editor_toolbar_state(markdown_active=True)
        self._update_note_header_label(absolute.name, dirty=False)

    def _display_pdf_document(self, absolute: Path) -> None:
        if self._note_renderer_stack is None or self._note_pdf_view is None:
            return
        if isinstance(self._note_pdf_view, QLabel) or self._note_pdf_document is None:
            self._note_renderer_stack.setCurrentWidget(self._note_pdf_view)
            self._note_current_type = "pdf"
            self._update_editor_toolbar_state(markdown_active=False)
            self._update_note_header_label(absolute.name, dirty=False)
            return
        status = self._note_pdf_document.load(str(absolute))
        if status != QPdfDocument.Status.NoError:  # type: ignore[attr-defined]
            self._show_note_error("PDF konnte nicht geladen werden.")
            return
        self._note_renderer_stack.setCurrentWidget(self._note_pdf_view)
        self._note_current_type = "pdf"
        self._update_editor_toolbar_state(markdown_active=False)
        self._update_note_header_label(absolute.name, dirty=False)

    def _show_note_placeholder(self, message: str) -> None:
        if self._note_renderer_stack is None or self._note_placeholder_label is None:
            return
        self._note_placeholder_label.setText(message)
        self._note_renderer_stack.setCurrentWidget(self._note_placeholder_label)
        self._update_editor_toolbar_state(markdown_active=False)
        self._update_note_header_label("Kein Dokument", dirty=False)

    def _show_note_error(self, message: str) -> None:
        if self._note_renderer_stack is None or self._note_error_label is None:
            return
        self._note_error_label.setText(message)
        self._note_renderer_stack.setCurrentWidget(self._note_error_label)
        self._update_editor_toolbar_state(markdown_active=False)

    # ------------------------------------------------------------------ #
    # Toolbar actions
    # ------------------------------------------------------------------ #
    def _handle_note_new_document(self) -> None:
        template = "# Neue Notiz\n\nText hier einfügen …\n"
        service = getattr(self, "_project_service", None)
        if service is None:
            notes_dir = DATA_DIR / "notes"
            notes_dir.mkdir(parents=True, exist_ok=True)
            target = notes_dir / f"note-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
            target.write_text(template, encoding="utf-8")
            reference = str(target)
        else:
            with tempfile.NamedTemporaryFile("w", delete=False, suffix=".md", encoding="utf-8") as handle:
                handle.write(template)
                tmp_path = Path(handle.name)
            try:
                reference = service.import_file("notes", str(tmp_path))
            finally:
                tmp_path.unlink(missing_ok=True)
        added = self._viewmodel.add_note_documents([reference])
        if added:
            self._populate_note_documents(select_path=added[-1])

    def _handle_note_save_requested(self) -> None:
        self._save_current_note_document()

    def _handle_note_text_changed(self) -> None:
        if self._note_current_type != "markdown":
            return
        self._note_dirty = True
        if self._note_active_file_label is not None and self._note_current_path:
            self._update_note_header_label(Path(self._note_current_path).name, dirty=True)
        self._update_editor_toolbar_state(markdown_active=True)

    def _toggle_text_format(self, mode: str) -> None:
        editor = self._note_editor
        if editor is None or self._note_current_type != "markdown":
            return
        cursor = editor.textCursor()
        if not cursor.hasSelection():
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        fmt = QTextCharFormat()
        current = cursor.charFormat()
        if mode == "bold":
            weight = QFont.Weight.Normal if current.fontWeight() > QFont.Weight.Normal else QFont.Weight.Bold
            fmt.setFontWeight(weight)
        elif mode == "italic":
            fmt.setFontItalic(not current.fontItalic())
        elif mode == "underline":
            fmt.setFontUnderline(not current.fontUnderline())
        elif mode == "strike":
            fmt.setFontStrikeOut(not current.fontStrikeOut())
        cursor.mergeCharFormat(fmt)
        editor.mergeCurrentCharFormat(fmt)

    def _toggle_list(self, style: QTextListFormat.Style) -> None:
        editor = self._note_editor
        if editor is None or self._note_current_type != "markdown":
            return
        cursor = editor.textCursor()
        cursor.beginEditBlock()
        current_list = cursor.currentList()
        if current_list and current_list.format().style() == style:
            block_format = QTextBlockFormat()
            current_list.remove(cursor.block())
            cursor.setBlockFormat(block_format)
        else:
            list_format = QTextListFormat()
            list_format.setStyle(style)
            cursor.createList(list_format)
        cursor.endEditBlock()

    def _toggle_block_quote(self) -> None:
        editor = self._note_editor
        if editor is None or self._note_current_type != "markdown":
            return
        cursor = editor.textCursor()
        cursor.beginEditBlock()
        current_format = cursor.blockFormat()
        is_quote = current_format.leftMargin() >= 16
        new_format = QTextBlockFormat()
        new_format.setLeftMargin(0 if is_quote else 24)
        new_format.setProperty(0, 0)
        cursor.mergeBlockFormat(new_format)
        cursor.endEditBlock()

    def _toggle_code_format(self) -> None:
        editor = self._note_editor
        if editor is None or self._note_current_type != "markdown":
            return
        cursor = editor.textCursor()
        if not cursor.hasSelection():
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        fmt = QTextCharFormat()
        current = cursor.charFormat()
        is_code = current.fontFixedPitch()
        fmt.setFontFixedPitch(not is_code)
        if is_code:
            fmt.clearProperty(QTextFormat.FontFamily)
        else:
            fmt.setFontFamily("Courier New")
        cursor.mergeCharFormat(fmt)
        editor.mergeCurrentCharFormat(fmt)

    def _apply_heading(self, level: int) -> None:
        editor = self._note_editor
        if editor is None or self._note_current_type != "markdown":
            return
        cursor = editor.textCursor()
        block_format = cursor.blockFormat()
        current_level = block_format.headingLevel()
        new_level = 0 if current_level == level else level
        cursor.beginEditBlock()
        block_format.setHeadingLevel(new_level)
        cursor.mergeBlockFormat(block_format)
        char_format = QTextCharFormat()
        if new_level == 0:
            char_format.setFontPointSize(self._note_default_font_size)
            char_format.setFontWeight(QFont.Weight.Normal)
        else:
            char_format.setFontPointSize(self._heading_font_size(new_level))
            char_format.setFontWeight(QFont.Weight.Bold)
        cursor.mergeCharFormat(char_format)
        cursor.endEditBlock()

    def _apply_paragraph(self) -> None:
        editor = self._note_editor
        if editor is None or self._note_current_type != "markdown":
            return
        cursor = editor.textCursor()
        block_format = cursor.blockFormat()
        block_format.setHeadingLevel(0)
        block_format.setLeftMargin(0)
        cursor.setBlockFormat(block_format)

    def _clear_formatting(self) -> None:
        editor = self._note_editor
        if editor is None or self._note_current_type != "markdown":
            return
        cursor = editor.textCursor()
        if not cursor.hasSelection():
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        cursor.beginEditBlock()
        char_format = QTextCharFormat()
        char_format.setFontWeight(QFont.Weight.Normal)
        char_format.setFontItalic(False)
        char_format.setFontUnderline(False)
        char_format.setFontStrikeOut(False)
        char_format.setFontFixedPitch(False)
        char_format.setFontPointSize(self._note_default_font_size)
        char_format.clearProperty(QTextFormat.FontFamily)
        cursor.mergeCharFormat(char_format)
        block_format = QTextBlockFormat()
        block_format.setHeadingLevel(0)
        block_format.setLeftMargin(0)
        cursor.setBlockFormat(block_format)
        current_list = cursor.currentList()
        if current_list:
            current_list.remove(cursor.block())
        cursor.endEditBlock()

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _is_supported_document(self, path: str) -> bool:
        suffix = Path(path).suffix.lower()
        return suffix in self.MARKDOWN_EXTENSIONS or suffix in self.PDF_EXTENSIONS

    def _heading_font_size(self, level: int) -> float:
        base = self._note_default_font_size
        increments = {1: 8.0, 2: 5.0, 3: 2.0}
        return max(base + increments.get(level, 0), base)

    @staticmethod
    def _resolve_default_font_size(editor: QTextEdit) -> float:
        size = editor.fontPointSize()
        if size <= 0:
            size = editor.font().pointSizeF()
        if size <= 0:
            size = 12.0
        return size

    def _update_editor_toolbar_state(self, *, markdown_active: bool) -> None:
        for key in (
            "clear",
            "heading1",
            "heading2",
            "heading3",
            "bold",
            "italic",
            "underline",
            "strike",
            "code",
            "quote",
            "bullet",
            "number",
        ):
            button = self._note_toolbar_buttons.get(key)
            if button is not None:
                button.setEnabled(markdown_active)
        save_button = self._note_toolbar_buttons.get("save")
        if save_button is not None:
            save_button.setEnabled(markdown_active and self._note_dirty)

    def _update_note_header_label(self, name: str, *, dirty: bool) -> None:
        label = self._note_active_file_label
        if label is None:
            return
        suffix = "*" if dirty else ""
        label.setText(name + suffix)

    def _save_current_note_document(self) -> bool:
        if self._note_current_type != "markdown" or not self._note_current_path or self._note_editor is None:
            return False
        absolute = self._resolve_note_path(self._note_current_path)
        absolute.parent.mkdir(parents=True, exist_ok=True)
        try:
            absolute.write_text(self._note_editor.toMarkdown(), encoding="utf-8")
        except OSError:
            return False
        self._note_dirty = False
        self._update_editor_toolbar_state(markdown_active=True)
        self._update_note_header_label(absolute.name, dirty=False)
        return True

    def _commit_note_changes_if_needed(self) -> bool:
        if not self._note_dirty:
            return True
        return self._save_current_note_document()

    def _resolve_note_path(self, reference: str | None) -> Path:
        if not reference:
            return Path("")
        candidate = Path(reference)
        if candidate.is_absolute():
            return candidate
        service = getattr(self, "_project_service", None)
        if service is not None:
            return service.resolve_asset_path(reference)
        return Path(resolve_media_path(reference))
