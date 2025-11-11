from __future__ import annotations

import json
import queue
import shutil
import tempfile
import threading
from pathlib import Path

from PySide6.QtCore import Qt, QEvent, QTimer, QObject, QUrl
from PySide6.QtGui import QAction, QIcon, QPalette, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSplitter,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from slidequest.models.slide import SlideData
from slidequest.services.project_service import ProjectStorageService
from slidequest.services.storage import SlideStorage
from slidequest.services.audio_service import AudioService
from slidequest.services.transcription_service import LiveTranscriptionService, RecordingResult
from slidequest.ui.constants import (
    ACTION_ICONS,
    DETAIL_HEADER_HEIGHT,
    EXPLORER_CRUD_SPECS,
    EXPLORER_FOOTER_HEIGHT,
    EXPLORER_HEADER_HEIGHT,
    STATUS_BAR_SIZE,
    SYMBOL_BUTTON_SIZE,
)
from slidequest.utils.media import slugify
from slidequest.viewmodels.master import MasterViewModel
from slidequest.views.master.explorer_section import ExplorerSectionMixin
from slidequest.views.master.notes_section import NotesSectionMixin
from slidequest.views.master.playlist_section import PlaylistSectionMixin
from slidequest.views.master.chrome_section import ChromeSectionMixin
from slidequest.views.presentation_window import PresentationWindow
from slidequest.views.widgets.common import IconBinding
from slidequest.views.widgets.layout_preview import LayoutPreviewCanvas, LayoutPreviewCard


class MasterWindow(
    PlaylistSectionMixin,
    NotesSectionMixin,
    ChromeSectionMixin,
    ExplorerSectionMixin,
    QMainWindow,
):
    """Top-level control surface for SlideQuest."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SlideQuest – Master")
        self.setMinimumSize(960, 600)
        self._project_status_bar: QFrame | None = None
        self._navigation_rail: QFrame | None = None
        self._project_title_label: QLabel | None = None
        self._trash_label: QLabel | None = None
        self._project_title_label: QLabel | None = None
        self._presentation_button: QToolButton | None = None
        self._explorer_container: QWidget | None = None
        self._presentation_window: PresentationWindow | None = None
        self._symbol_buttons: list[QToolButton] = []
        self._symbol_button_map: dict[str, QToolButton] = {}
        self._status_buttons: list[QToolButton] = []
        self._status_button_map: dict[str, QToolButton] = {}
        self._header_views: list[QFrame] = []
        self._detail_container: QWidget | None = None
        self._detail_stack: QStackedWidget | None = None
        self._detail_view_widgets: dict[str, QWidget] = {}
        self._detail_mode_buttons: dict[str, QToolButton | None] = {}
        self._detail_active_mode: str | None = None
        self._line_edit_actions: list[tuple[QAction, Path]] = []
        self._search_input: QLineEdit | None = None
        self._filter_button: QToolButton | None = None
        self._crud_buttons: list[QToolButton] = []
        self._crud_button_map: dict[str, QToolButton] = {}
        self._volume_slider: QSlider | None = None
        self._volume_button_map: dict[str, QToolButton] = {}
        self._last_volume_value = 75
        self._icon_bindings: list[IconBinding] = []
        self._playlist_accent_color = self.palette().color(QPalette.ColorRole.Highlight)
        self._audio_service = AudioService()
        self._project_service = ProjectStorageService()
        self._storage = SlideStorage(self._project_service)
        self._viewmodel = MasterViewModel(self._storage, project_service=self._project_service)
        self._viewmodel.add_listener(self._on_viewmodel_changed)
        self._transcription_service = LiveTranscriptionService(self._project_service)
        self._transcription_service.recording_failed.connect(self._handle_transcription_failure)
        self._transcription_service.recording_completed.connect(self._handle_async_recording_completed)
        self._transcription_service.transcript_updated.connect(self._handle_transcript_updated)
        self._recording_enabled = False
        self._pending_recording_restart = False
        self._finalizing_recording = False
        self._record_button: QToolButton | None = None
        self._record_button_live = False
        self._active_transcript_note: str | None = None
        self._slides: list[SlideData] = self._viewmodel.slides
        self._slide_list: QListWidget | None = None
        self._current_slide: SlideData | None = None
        self._detail_preview_canvas: LayoutPreviewCanvas | None = None
        self._related_layout_layout: QHBoxLayout | None = None
        self._related_layout_cards: list[LayoutPreviewCard] = []
        self._current_layout_id: str = ""
        self._icon_base_color = self.palette().color(QPalette.ColorRole.Text)
        self._icon_accent_color = self.palette().color(QPalette.ColorRole.Highlight)
        self._container_color = self.palette().color(QPalette.ColorRole.Window)
        self._content_splitter: QSplitter | None = None
        self._detail_last_sizes: list[int] = []
        self._setup_placeholder()
        self._update_project_title_label()
        self._update_trash_label()
        self._update_project_title_label()

    def _apply_surface_theme(self) -> None:  # type: ignore[override]
        super()._apply_surface_theme()
        self._refresh_slide_item_styles()

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if obj is self._content_splitter and event.type() in {QEvent.Type.Resize, QEvent.Type.Show}:
            QTimer.singleShot(0, self._apply_splitter_sizes)
        return super().eventFilter(obj, event)

    def _setup_placeholder(self) -> None:
        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        status_bar = QFrame(central)
        status_bar.setObjectName("ProjectStatusBar")
        status_bar.setFixedHeight(STATUS_BAR_SIZE)
        self._project_status_bar = status_bar
        self._build_status_bar(status_bar)
        self._record_button = self._status_button_map.get("ProjectRecordButton")

        viewport = QFrame(central)
        viewport.setObjectName("AppViewport")
        viewport_layout = QHBoxLayout(viewport)
        viewport_layout.setContentsMargins(0, 0, 0, 0)
        viewport_layout.setSpacing(0)

        symbol_view = self._build_symbol_view(viewport)

        splitter = QSplitter(Qt.Orientation.Horizontal, viewport)
        splitter.setObjectName("ContentSplitter")
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(8)
        self._content_splitter = splitter

        explorer_container = QWidget(splitter)
        explorer_container.setObjectName("ExplorerView")
        self._explorer_container = explorer_container
        explorer_layout = QVBoxLayout(explorer_container)
        explorer_layout.setContentsMargins(0, 0, 0, 0)
        explorer_layout.setSpacing(0)

        explorer_header = QFrame(explorer_container)
        explorer_header.setObjectName("ExplorerHeader")
        explorer_header.setFixedHeight(EXPLORER_HEADER_HEIGHT)
        self._header_views.append(explorer_header)
        explorer_header_layout = QHBoxLayout(explorer_header)
        explorer_header_layout.setContentsMargins(8, 4, 8, 4)
        explorer_header_layout.setSpacing(8)

        search_input = QLineEdit(explorer_header)
        search_input.setObjectName("ExplorerSearchField")
        search_input.setPlaceholderText("Suche …")
        search_input.setToolTip("ExplorerSearchField")
        search_input.setFixedHeight(SYMBOL_BUTTON_SIZE)
        search_action = search_input.addAction(
            QIcon(str(ACTION_ICONS["search"])),
            QLineEdit.ActionPosition.LeadingPosition,
        )
        self._line_edit_actions.append((search_action, ACTION_ICONS["search"]))
        self._search_input = search_input

        filter_button = self._create_icon_button(
            explorer_header,
            "ExplorerFilterButton",
            ACTION_ICONS["filter"],
            "Filter öffnen",
            checkable=True,
        )
        filter_button.setFixedSize(SYMBOL_BUTTON_SIZE, SYMBOL_BUTTON_SIZE)
        self._filter_button = filter_button

        explorer_header_layout.addWidget(search_input, 1)
        explorer_header_layout.addWidget(filter_button)

        explorer_footer = QFrame(explorer_container)
        explorer_footer.setObjectName("ExplorerFooter")
        explorer_footer.setFixedHeight(EXPLORER_FOOTER_HEIGHT)

        explorer_main_scroll = QScrollArea(explorer_container)
        explorer_main_scroll.setObjectName("ExplorerMainScroll")
        explorer_main_scroll.setWidgetResizable(True)
        explorer_main_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        explorer_main_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        explorer_main_scroll.setStyleSheet("QScrollBar { width: 0px; }")
        explorer_main_scroll.setFrameShape(QFrame.Shape.NoFrame)

        explorer_main = QWidget()
        explorer_main.setObjectName("ExplorerMainView")
        explorer_main_layout = QVBoxLayout(explorer_main)
        explorer_main_layout.setContentsMargins(4, 4, 4, 4)
        explorer_main_layout.setSpacing(4)
        self._slide_list = QListWidget(explorer_main)
        self._slide_list.setObjectName("SlideListView")
        self._slide_list.setFrameShape(QFrame.Shape.NoFrame)
        self._slide_list.viewport().setAutoFillBackground(False)
        self._slide_list.setStyleSheet(
            """
            QListWidget#SlideListView {
                background-color: transparent;
                border: none;
            }
            QListWidget#SlideListView::item {
                background-color: transparent;
                border: none;
            }
            """
        )
        self._slide_list.setSpacing(6)
        explorer_main_layout.addWidget(self._slide_list)
        explorer_main_scroll.setWidget(explorer_main)
        self._slide_list.currentItemChanged.connect(
            lambda current, _prev: self._on_slide_selected(current)
        )
        self._populate_slide_list()

        explorer_layout.addWidget(explorer_header)
        explorer_layout.addWidget(explorer_main_scroll, 1)
        explorer_layout.addWidget(explorer_footer)
        explorer_footer_layout = QHBoxLayout(explorer_footer)
        explorer_footer_layout.setContentsMargins(8, 4, 8, 4)
        explorer_footer_layout.setSpacing(8)
        explorer_footer_layout.addStretch(1)
        self._crud_button_map = self._build_buttons(
            explorer_footer,
            explorer_footer_layout,
            EXPLORER_CRUD_SPECS,
            size=SYMBOL_BUTTON_SIZE,
            registry=self._crud_buttons,
        )
        if create_button := self._crud_button_map.get("ExplorerCreateButton"):
            create_button.clicked.connect(self._handle_create_slide)
        if delete_button := self._crud_button_map.get("ExplorerDeleteButton"):
            delete_button.clicked.connect(self._handle_delete_slide)

        detail_container = QWidget(splitter)
        detail_container.setObjectName("DetailView")
        self._detail_container = detail_container
        detail_layout = QVBoxLayout(detail_container)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(0)

        detail_stack = QStackedWidget(detail_container)
        detail_stack.setObjectName("DetailStack")
        detail_layout.addWidget(detail_stack, 1)
        self._detail_stack = detail_stack

        layout_detail = QWidget(detail_stack)
        layout_detail.setObjectName("LayoutDetailView")
        layout_detail_layout = QVBoxLayout(layout_detail)
        layout_detail_layout.setContentsMargins(0, 0, 0, 0)
        layout_detail_layout.setSpacing(0)

        detail_header = QFrame(layout_detail)
        detail_header.setObjectName("DetailHeader")
        detail_header.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        detail_header.setFixedHeight(DETAIL_HEADER_HEIGHT)
        self._header_views.append(detail_header)
        detail_header_layout = QHBoxLayout(detail_header)
        detail_header_layout.setContentsMargins(12, 6, 12, 6)
        detail_header_layout.setSpacing(8)

        detail_header_layout.addStretch(1)

        detail_footer = QFrame(layout_detail)
        detail_footer.setObjectName("DetailFooter")
        detail_footer.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        detail_footer.setMinimumHeight(220)
        detail_footer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        detail_footer.setVisible(True)

        detail_main_scroll = QScrollArea(layout_detail)
        detail_main_scroll.setObjectName("DetailMainScroll")
        detail_main_scroll.setWidgetResizable(True)
        detail_main_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        detail_main_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        detail_main_scroll.setStyleSheet("QScrollBar { width: 0px; }")
        detail_main_scroll.setFrameShape(QFrame.Shape.NoFrame)

        detail_main = QWidget()
        detail_main.setObjectName("DetailMainView")
        detail_main_layout = QVBoxLayout(detail_main)
        detail_main_layout.setContentsMargins(12, 12, 12, 12)
        detail_main_layout.setSpacing(12)

        initial_layout = self._slides[0].layout.active_layout if self._slides else "1S|100/1R|100"
        initial_images = self._slides[0].images.copy() if self._slides else {}
        self._current_layout_id = initial_layout
        self._detail_preview_canvas = LayoutPreviewCanvas(initial_layout, detail_main, accepts_drop=True)
        self._detail_preview_canvas.setObjectName("DetailPreviewCanvas")
        self._detail_preview_canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._detail_preview_canvas.areaDropped.connect(self._handle_preview_drop)
        detail_main_layout.addWidget(self._detail_preview_canvas, 1)
        if initial_images:
            self._detail_preview_canvas.set_area_images(self._resolve_image_paths(initial_images))
        self._sync_preview_with_current_slide()

        detail_footer_layout = QVBoxLayout(detail_footer)
        detail_footer_layout.setContentsMargins(12, 8, 12, 12)
        detail_footer_layout.setSpacing(8)
        related_scroll = QScrollArea(detail_footer)
        related_scroll.setObjectName("LayoutSelectorScroll")
        related_scroll.setWidgetResizable(True)
        related_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        related_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        related_scroll.setStyleSheet("QScrollBar:horizontal { height: 0px; }")
        related_scroll.setFrameShape(QFrame.Shape.NoFrame)

        related_items_container = QWidget()
        related_items_container.setObjectName("LayoutSelectorContainer")
        horizontal_layout = QHBoxLayout(related_items_container)
        horizontal_layout.setContentsMargins(0, 0, 0, 0)
        horizontal_layout.setSpacing(8)
        related_scroll.setWidget(related_items_container)
        detail_footer_layout.addWidget(related_scroll)

        self._related_layout_layout = horizontal_layout
        self._populate_related_layouts()

        detail_main_scroll.setWidget(detail_main)

        layout_detail_layout.addWidget(detail_header)
        layout_detail_layout.addWidget(detail_main_scroll, 1)
        layout_detail_layout.addWidget(detail_footer)
        detail_stack.addWidget(layout_detail)
        self._detail_view_widgets["layout"] = layout_detail

        playlist_detail = self._build_playlist_detail_view(detail_stack)
        detail_stack.addWidget(playlist_detail)
        self._detail_view_widgets["audio"] = playlist_detail

        notes_detail = self._build_notes_detail_view(detail_stack)
        detail_stack.addWidget(notes_detail)
        self._detail_view_widgets["notes"] = notes_detail

        splitter.addWidget(explorer_container)
        splitter.addWidget(detail_container)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.installEventFilter(self)
        self._apply_splitter_sizes()

        viewport_layout.addWidget(symbol_view)
        viewport_layout.addWidget(splitter, 1)

        layout.addWidget(status_bar)
        layout.addWidget(viewport, 1)
        central.setLayout(layout)
        self.setCentralWidget(central)
        self._apply_surface_theme()
        self._wire_symbol_launchers()
        self._wire_audio_service()

    def _on_viewmodel_changed(self) -> None:
        self._slides = self._viewmodel.slides
        self._populate_playlist_tracks()
        self._populate_note_documents()
        self._update_trash_label()

    def attach_presentation_window(self, window: PresentationWindow) -> None:
        """Register an external presentation window instance."""
        self._presentation_window = window
        window.closed.connect(self._on_presentation_closed)
        self._sync_preview_with_current_slide()

    def _wire_symbol_launchers(self) -> None:
        layout_button = self._symbol_button_map.get("LayoutExplorerLauncher")
        audio_button = self._symbol_button_map.get("AudioExplorerLauncher")
        note_button = self._symbol_button_map.get("NoteExplorerLauncher")
        self._detail_mode_buttons = {
            "layout": layout_button,
            "audio": audio_button,
            "notes": note_button,
        }
        handlers_connected = False
        for mode, button in self._detail_mode_buttons.items():
            if button is None:
                continue
            handlers_connected = True
            button.toggled.connect(lambda checked, mode=mode: self._handle_detail_launcher_toggled(mode, checked))
        if handlers_connected:
            self._initialize_detail_view_state()

    def _initialize_detail_view_state(self) -> None:
        active_mode = self._resolve_checked_detail_mode()
        if active_mode:
            self._activate_detail_mode(active_mode)
        else:
            self._set_detail_views_visible(False)
        self._apply_splitter_sizes()

    def _wire_audio_service(self) -> None:
        service = self._audio_service
        service.track_state_changed.connect(self._handle_audio_track_state_changed)
        service.position_changed.connect(self._handle_audio_position_changed)
        service.duration_changed.connect(self._handle_audio_duration_changed)

    # ------------------------------------------------------------------ #
    # Project actions
    # ------------------------------------------------------------------ #
    def _handle_project_new_clicked(self) -> None:
        name, ok = QInputDialog.getText(self, "Neues Projekt", "Projektname:")
        if not ok:
            return
        slug = slugify(name.strip())
        if not slug:
            QMessageBox.warning(self, "Projekt", "Bitte einen gültigen Namen eingeben.")
            return
        target = self._project_service.projects_root / slug
        if target.exists():
            QMessageBox.warning(self, "Projekt", "Ein Projekt mit diesem Namen existiert bereits.")
            return
        target.mkdir(parents=True, exist_ok=True)
        self._switch_project(slug, self._project_service.base_dir)

    def _handle_project_open_clicked(self) -> None:
        projects = self._project_service.list_projects()
        if not projects:
            QMessageBox.information(self, "Projekt öffnen", "Es wurden keine Projekte gefunden.")
            return
        selection, ok = QInputDialog.getItem(
            self,
            "Projekt öffnen",
            "Projekt auswählen:",
            projects,
            editable=False,
        )
        if not ok or not selection:
            return
        self._switch_project(selection, self._project_service.base_dir)

    def _handle_project_export_clicked(self) -> None:
        project_dir = self._project_service.project_dir
        project_dir.mkdir(parents=True, exist_ok=True)
        default_name = f"{self._project_service.project_id}.sq"
        target_path, _ = QFileDialog.getSaveFileName(
            self,
            "Projekt exportieren",
            default_name,
            "SlideQuest Projekt (*.sq)",
        )
        if not target_path:
            return
        destination = Path(target_path)
        if destination.suffix.lower() != ".sq":
            destination = destination.with_suffix(".sq")
        workspace = Path(tempfile.mkdtemp())
        try:
            export_root = workspace / "project"
            shutil.copytree(project_dir, export_root)
            trash = export_root / ".trash"
            if trash.exists():
                shutil.rmtree(trash, ignore_errors=True)
            archive = shutil.make_archive(str(workspace / "export"), "zip", root_dir=export_root)
            shutil.move(archive, destination)
        finally:
            shutil.rmtree(workspace, ignore_errors=True)
        QMessageBox.information(self, "Projekt exportieren", f"Export gespeichert unter:\n{destination}")

    def _handle_project_import_clicked(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Projekt importieren",
            "",
            "SlideQuest Projekt (*.sq)",
        )
        if not file_path:
            return
        source = Path(file_path)
        if not source.exists():
            QMessageBox.warning(self, "Projekt importieren", "Die Datei wurde nicht gefunden.")
            return
        temp_dir = tempfile.mkdtemp()
        temp_path = Path(temp_dir)
        try:
            shutil.unpack_archive(str(source), temp_dir)
            project_json = temp_path / "project.json"
            if not project_json.exists():
                QMessageBox.warning(self, "Projekt importieren", "Ungültiges Projektpaket.")
                return
            data = json.loads(project_json.read_text(encoding="utf-8"))
            project_id = data.get("id") or slugify(source.stem)
            target = self._project_service.projects_root / project_id
            if target.exists():
                QMessageBox.warning(self, "Projekt importieren", "Projekt existiert bereits.")
                return
            shutil.copytree(temp_path, target)
            self._switch_project(project_id, self._project_service.base_dir)
        finally:
            shutil.rmtree(temp_path, ignore_errors=True)

    def _handle_project_reveal_clicked(self) -> None:
        directory = self._project_service.project_dir
        directory.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(directory)))

    def _handle_project_prune_clicked(self) -> None:
        trash_dir = self._project_service.project_dir / ".trash"
        if trash_dir.exists():
            shutil.rmtree(trash_dir, ignore_errors=True)
        self._update_trash_label()

    def _handle_project_record_toggled(self, checked: bool) -> None:
        if checked:
            if not self._ensure_transcription_ready():
                self._set_record_button_checked(False)
                return
            if not self._confirm_model_download_if_needed():
                self._set_record_button_checked(False)
                return
            if self._current_slide is None:
                self._show_transcription_message("Bitte wähle zuerst eine Folie aus.", error=True)
                self._set_record_button_checked(False)
                return
            self._recording_enabled = True
            self._pending_recording_restart = False
            try:
                self._start_recording_for_current_slide()
            except RuntimeError as exc:
                self._recording_enabled = False
                self._set_record_button_checked(False)
                self._show_transcription_message(str(exc), error=True)
        else:
            self._recording_enabled = False
            self._pending_recording_restart = False
            self._finalize_recording_session()
            if not self._transcription_service.is_recording:
                self._set_record_button_live(False)

    def _update_trash_label(self) -> None:
        label = getattr(self, "_trash_label", None)
        if label is None:
            return
        size_bytes = self._project_service.trash_size()
        size_mb = size_bytes / (1024 * 1024)
        label.setText(f"Papierkorb: {size_mb:.1f} MB")

    def _switch_project(self, project_id: str, base_dir: Path | None = None) -> None:
        base = base_dir or self._project_service.base_dir
        self._project_service = ProjectStorageService(project_id=project_id, base_dir=base)
        self._storage = SlideStorage(self._project_service)
        self._viewmodel = MasterViewModel(self._storage, project_service=self._project_service)
        self._viewmodel.add_listener(self._on_viewmodel_changed)
        self._slides = self._viewmodel.slides
        self._populate_slide_list()
        self._populate_playlist_tracks()
        self._populate_note_documents()
        self._update_project_title_label()
        self._update_trash_label()

    def _ensure_transcription_ready(self) -> bool:
        if self._transcription_service.is_available:
            return True
        self._show_transcription_message(
            "Live-Transkription steht nicht zur Verfügung. Installiere numpy, sounddevice und faster-whisper.",
            error=True,
        )
        return False

    def _confirm_model_download_if_needed(self) -> bool:
        if not self._transcription_service.requires_model_download:
            return True
        warning_text = (
            "Das Whisper-Large-Modell muss einmalig heruntergeladen werden "
            "(≈6 GB Download, empfohlen ≥10 GB Grafikspeicher/16 GB RAM). "
            "Möchtest du den Download jetzt starten?"
        )
        result = QMessageBox.warning(
            self,
            "Whisper-Large herunterladen?",
            warning_text,
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if result != QMessageBox.StandardButton.Ok:
            return False
        return self._download_model_with_progress()

    def _download_model_with_progress(self) -> bool:
        progress_dialog = QProgressDialog("Bereite Download vor …", "", 0, 100, self)
        progress_dialog.setWindowTitle("Whisper-Large Download")
        progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        progress_dialog.setCancelButton(None)
        progress_dialog.setMinimumDuration(0)
        progress_dialog.setValue(0)
        progress_dialog.show()

        updates: queue.Queue[tuple[str, object, object]] = queue.Queue()

        def progress_callback(current: int, total: int) -> None:
            updates.put(("progress", current, total))

        def worker() -> None:
            try:
                self._transcription_service.download_model(progress_callback=progress_callback)
                updates.put(("done", True, None))
            except Exception as exc:
                updates.put(("done", False, str(exc)))

        download_thread = threading.Thread(target=worker, daemon=True)
        download_thread.start()
        success = False
        error_message: str | None = None
        finished = False
        while not finished:
            QApplication.processEvents()
            try:
                kind, value1, value2 = updates.get(timeout=0.05)
            except queue.Empty:
                if not download_thread.is_alive() and updates.empty():
                    finished = True
                continue
            if kind == "progress":
                current = int(value1)
                total = int(value2) or 1
                percent = int(current / max(1, total) * 100)
                progress_dialog.setValue(percent)
                current_mb = current / (1024 * 1024)
                total_mb = total / (1024 * 1024)
                progress_dialog.setLabelText(
                    f"Lade Whisper Large … {current_mb:.1f} / {total_mb:.1f} MB"
                )
            elif kind == "done":
                success = bool(value1)
                error_message = value2 if isinstance(value2, str) else None
                finished = True
        download_thread.join(timeout=0.5)
        progress_dialog.close()
        if not success or self._transcription_service.requires_model_download:
            self._show_transcription_message(
                f"Das Whisper-Modell konnte nicht geladen werden.\n{error_message or ''}".strip(),
                error=True,
            )
            return False
        self._show_transcription_message("Whisper-Large wurde erfolgreich installiert.")
        return True

    def _prepare_live_transcript_note(self) -> tuple[str, str] | None:
        slide = self._current_slide
        if slide is None:
            return None
        title = slide.title or f"Folie {self._viewmodel.current_index + 1}"
        header = f"# Live-Transkript – {title}\n\n"
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".md", encoding="utf-8") as handle:
            handle.write(header)
            tmp_path = Path(handle.name)
        try:
            relative = self._project_service.import_file("notes", str(tmp_path))
        finally:
            tmp_path.unlink(missing_ok=True)
        self._viewmodel.attach_note_reference(self._viewmodel.current_index, relative)
        self._populate_note_documents(select_path=relative)
        absolute = str(self._project_service.resolve_asset_path(relative))
        return relative, absolute

    def _start_recording_for_current_slide(self) -> None:
        if not self._recording_enabled or self._current_slide is None:
            return
        index = self._viewmodel.current_index
        if index < 0:
            return
        if (
            self._transcription_service.is_recording
            and self._transcription_service.current_slide_index == index
        ):
            return
        title = self._current_slide.title or f"Folie {index + 1}"
        note_refs = self._prepare_live_transcript_note()
        if note_refs is None:
            return
        relative_note, absolute_note = note_refs
        self._active_transcript_note = relative_note
        self._transcription_service.start(index, title, transcript_path=absolute_note)
        self._set_record_button_live(True)

    def _finalize_recording_session(self, restart_after: bool = False) -> None:
        self._pending_recording_restart = restart_after
        if self._finalizing_recording:
            return
        self._finalizing_recording = True
        self._transcription_service.stop_async()

    def _apply_recording_result(self, result: RecordingResult | None) -> None:
        if result is None or not result.transcript_path:
            return
        self._viewmodel.attach_note_reference(result.slide_index, result.transcript_path)
        if self._viewmodel.current_index == result.slide_index:
            self._populate_note_documents(select_path=result.transcript_path)

    def _handle_async_recording_completed(self, result: RecordingResult | None) -> None:
        self._finalizing_recording = False
        self._apply_recording_result(result)
        restart = self._pending_recording_restart
        self._pending_recording_restart = False
        if restart and self._recording_enabled:
            try:
                self._start_recording_for_current_slide()
            except RuntimeError as exc:
                self._show_transcription_message(str(exc), error=True)
                self._recording_enabled = False
                self._set_record_button_live(False)
                self._set_record_button_checked(False)
        else:
            self._set_record_button_live(False)
        self._active_transcript_note = None

    def _handle_recording_before_slide_change(self) -> None:  # type: ignore[override]
        if not self._recording_enabled:
            return
        self._finalize_recording_session(restart_after=True)

    def _handle_slide_selection_completed(self, slide: SlideData | None) -> None:  # type: ignore[override]
        if not self._recording_enabled or slide is None:
            return
        if self._pending_recording_restart or not self._transcription_service.is_recording:
            try:
                self._start_recording_for_current_slide()
            except RuntimeError as exc:
                self._show_transcription_message(str(exc), error=True)
                self._recording_enabled = False
                self._set_record_button_checked(False)
        self._pending_recording_restart = False

    def _handle_transcription_failure(self, message: str) -> None:
        self._pending_recording_restart = False
        self._finalizing_recording = True
        self._transcription_service.stop_async()
        self._recording_enabled = False
        self._pending_recording_restart = False
        self._set_record_button_live(False)
        self._set_record_button_checked(False)
        if message:
            self._show_transcription_message(message, error=True)
        self._active_transcript_note = None

    def _set_record_button_checked(self, checked: bool) -> None:
        button = self._record_button or self._status_button_map.get("ProjectRecordButton")
        if button is None or button.isChecked() == checked:
            return
        button.blockSignals(True)
        button.setChecked(checked)
        button.blockSignals(False)

    def _set_record_button_live(self, live: bool) -> None:
        if self._record_button_live == live:
            return
        self._record_button_live = live
        self._update_icon_colors()

    def _show_transcription_message(self, message: str, *, error: bool = False) -> None:
        text = message or "Live-Transkription fehlgeschlagen."
        if error:
            QMessageBox.warning(self, "Live-Transkription", text)
        else:
            QMessageBox.information(self, "Live-Transkription", text)

    def _handle_transcript_updated(self, slide_index: int, _text: str) -> None:
        if self._active_transcript_note is None:
            return
        if slide_index != self._viewmodel.current_index:
            return
        self._load_note_document(self._active_transcript_note)

    def _update_project_title_label(self) -> None:
        label = getattr(self, "_project_title_label", None)
        if label is None:
            return
        label.setText(self._project_service.project_id or "SlideQuest")

    def _handle_detail_launcher_toggled(self, mode: str, checked: bool) -> None:
        if checked:
            self._activate_detail_mode(mode)
            return
        replacement_mode = self._resolve_checked_detail_mode(exclude=mode)
        if replacement_mode:
            self._activate_detail_mode(replacement_mode)
            return
        if self._detail_active_mode == mode:
            self._detail_active_mode = None
            self._set_detail_views_visible(False)

    def _resolve_checked_detail_mode(self, exclude: str | None = None) -> str | None:
        for mode, button in self._detail_mode_buttons.items():
            if exclude and mode == exclude:
                continue
            if button is not None and button.isChecked():
                return mode
        return None

    def _activate_detail_mode(self, mode: str) -> None:
        stack = self._detail_stack
        widget = self._detail_view_widgets.get(mode)
        if stack is None or widget is None:
            return
        stack.setCurrentWidget(widget)
        self._detail_active_mode = mode
        self._set_detail_views_visible(True)

    def _set_detail_views_visible(self, visible: bool) -> None:
        detail = self._detail_container
        splitter = self._content_splitter
        if detail is None:
            return
        if visible:
            detail.show()
            if splitter:
                if len(self._detail_last_sizes) >= 2:
                    splitter.setSizes(self._detail_last_sizes)
                else:
                    self._apply_splitter_sizes()
        else:
            if splitter:
                sizes = splitter.sizes()
                if sizes:
                    self._detail_last_sizes = sizes
                    if len(sizes) >= 2:
                        explorer_total = sizes[0] + sizes[1]
                        splitter.setSizes([explorer_total, 0])
            detail.hide()

    def _apply_splitter_sizes(self) -> None:
        splitter = self._content_splitter
        explorer = self._explorer_container
        if splitter is None or explorer is None:
            return
        total = splitter.width() or self.width()
        if total <= 0:
            return
        desired = max(300, min(explorer.sizeHint().width(), int(total * 0.2)))
        detail_width = max(total - desired, desired)
        splitter.blockSignals(True)
        splitter.setSizes([desired, detail_width])
        splitter.blockSignals(False)

    def _enforce_splitter_ratio(self, _pos: int, _index: int) -> None:
        self._apply_splitter_sizes()

    def _wire_volume_buttons(self, buttons: dict[str, QToolButton]) -> None:
        slider = self._volume_slider
        if slider is None:
            return

        def adjust(delta: int) -> None:
            slider.setValue(max(0, min(100, slider.value() + delta)))

        mute = buttons.get("StatusMuteButton")
        if mute is not None:
            def handle_mute(checked: bool) -> None:
                if checked:
                    self._last_volume_value = slider.value()
                    slider.setValue(0)
                else:
                    slider.setValue(self._last_volume_value)

            mute.toggled.connect(handle_mute)

        def remember_volume(value: int) -> None:
            if mute is None or not mute.isChecked():
                self._last_volume_value = value

        slider.valueChanged.connect(remember_volume)

        if vol_down := buttons.get("StatusVolumeDownButton"):
            vol_down.clicked.connect(lambda: adjust(-5))
        if vol_up := buttons.get("StatusVolumeUpButton"):
            vol_up.clicked.connect(lambda: adjust(5))

    @staticmethod
    def _format_time(seconds: float) -> str:
        if seconds <= 0:
            return "00:00"
        minutes = int(seconds) // 60
        remainder = int(seconds) % 60
        return f"{minutes:02d}:{remainder:02d}"

    def _show_presentation_window(self) -> None:
        window = self._presentation_window
        if window is None:
            window = PresentationWindow()
            self.attach_presentation_window(window)
        if window.isVisible():
            return
        window.show()
        if self._presentation_button is not None:
            self._presentation_button.setEnabled(False)

    def _on_presentation_closed(self) -> None:
        if self._presentation_button is not None:
            self._presentation_button.setEnabled(True)
        self._presentation_window = None
