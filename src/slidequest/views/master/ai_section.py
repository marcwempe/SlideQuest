from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QInputDialog,
    QLineEdit,
)

from slidequest.services.replicate_service import ReplicateService
from slidequest.ui.constants import ACTION_ICONS
from slidequest.views.widgets.replicate_gallery import ReplicateGalleryWidget


class AISectionMixin:
    """Builds and wires the Replicate Seedream detail view + drawer."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[misc]
        self._replicate_service: ReplicateService | None = None
        self._ai_prompt_input: QTextEdit | None = None
        self._ai_size_combo: QComboBox | None = None
        self._ai_aspect_combo: QComboBox | None = None
        self._ai_width_spin: QSpinBox | None = None
        self._ai_height_spin: QSpinBox | None = None
        self._ai_max_images_spin: QSpinBox | None = None
        self._ai_enhance_check: QCheckBox | None = None
        self._ai_status_label: QLabel | None = None
        self._ai_generate_button: QPushButton | None = None
        self._ai_gallery: ReplicateGalleryWidget | None = None
        self._ai_drawer_gallery: ReplicateGalleryWidget | None = None
        self._ai_drawer: QFrame | None = None
        self._ai_drawer_toggle: QToolButton | None = None
        self._ai_drawer_expanded = 160
        self._ai_drawer_thumb = QSize(112, 112)
        self._ai_request_meta: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------------ #
    # Service wiring
    # ------------------------------------------------------------------ #
    def _init_ai_service(self) -> None:
        service = self._replicate_service
        if service is None:
            return
        service.generation_started.connect(self._handle_ai_generation_started)
        service.generation_progress.connect(self._handle_ai_generation_progress)
        service.generation_failed.connect(self._handle_ai_generation_failed)
        service.generation_finished.connect(self._handle_ai_generation_finished)

    # ------------------------------------------------------------------ #
    # Detail View
    # ------------------------------------------------------------------ #
    def _build_ai_detail_view(self, parent: QWidget | None = None) -> QWidget:
        view = QWidget(parent)
        view.setObjectName("AISeedreamDetailView")
        layout = QVBoxLayout(view)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame(view)
        header.setObjectName("AISeedreamHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 8, 12, 8)
        header_layout.setSpacing(8)
        title = QLabel("Seedream 4 – Replicate Integration", header)
        title.setObjectName("AISeedreamTitle")
        title.setStyleSheet("font-weight: 600; letter-spacing: 0.4px;")
        header_layout.addWidget(title, 1)
        layout.addWidget(header)

        prompt = QTextEdit(view)
        prompt.setObjectName("AISeedreamPrompt")
        prompt.setPlaceholderText("Beschreibe die gewünschte Szene …")
        prompt.setFixedHeight(140)
        prompt.setStyleSheet(
            """
            QTextEdit#AISeedreamPrompt {
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 12px;
                padding: 10px 12px;
                font-size: 13px;
            }
            QTextEdit#AISeedreamPrompt:focus {
                border-color: rgba(120, 190, 255, 0.9);
            }
            """
        )
        self._ai_prompt_input = prompt
        layout.addWidget(prompt)
        layout.addSpacing(8)

        controls = QFrame(view)
        controls.setObjectName("AISeedreamControls")
        controls_layout = QGridLayout(controls)
        controls_layout.setContentsMargins(12, 12, 12, 12)
        controls_layout.setHorizontalSpacing(12)
        controls_layout.setVerticalSpacing(12)
        controls.setStyleSheet(
            """
            QFrame#AISeedreamControls {
                background-color: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 14px;
            }
            QComboBox[aiControl="true"],
            QSpinBox[aiControl="true"] {
                background-color: rgba(0, 0, 0, 0.35);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                padding: 4px 10px;
                color: rgba(255, 255, 255, 0.9);
                min-height: 30px;
            }
            QComboBox[aiControl="true"]:focus,
            QSpinBox[aiControl="true"]:focus {
                border-color: rgba(120, 190, 255, 0.85);
            }
            QCheckBox#AISeedreamEnhance {
                color: rgba(255, 255, 255, 0.85);
            }
            """
        )

        size_combo = QComboBox(controls)
        size_combo.addItem("1K (1024 px)", "1K")
        size_combo.addItem("2K (2048 px)", "2K")
        size_combo.addItem("4K (4096 px)", "4K")
        size_combo.addItem("Benutzerdefiniert", "custom")
        size_combo.setCurrentIndex(1)
        size_combo.currentIndexChanged.connect(self._handle_ai_size_mode_changed)
        self._ai_size_combo = size_combo
        size_combo.setProperty("aiControl", True)
        controls_layout.addWidget(QLabel("Auflösung", controls), 0, 0)
        controls_layout.addWidget(size_combo, 0, 1)

        aspect_combo = QComboBox(controls)
        aspect_combo.addItem("Input beibehalten", "match_input_image")
        aspect_combo.addItem("Quadrat 1:1", "1:1")
        aspect_combo.addItem("4:3", "4:3")
        aspect_combo.addItem("3:2", "3:2")
        aspect_combo.addItem("16:9", "16:9")
        aspect_combo.addItem("9:16", "9:16")
        self._ai_aspect_combo = aspect_combo
        aspect_combo.setProperty("aiControl", True)
        controls_layout.addWidget(QLabel("Seitenverhältnis", controls), 1, 0)
        controls_layout.addWidget(aspect_combo, 1, 1)

        width_spin = QSpinBox(controls)
        width_spin.setRange(1024, 4096)
        width_spin.setSingleStep(64)
        width_spin.setValue(2048)
        width_spin.setEnabled(False)
        self._ai_width_spin = width_spin
        width_spin.setProperty("aiControl", True)
        controls_layout.addWidget(QLabel("Breite (Custom)", controls), 0, 2)
        controls_layout.addWidget(width_spin, 0, 3)

        height_spin = QSpinBox(controls)
        height_spin.setRange(1024, 4096)
        height_spin.setSingleStep(64)
        height_spin.setValue(2048)
        height_spin.setEnabled(False)
        self._ai_height_spin = height_spin
        height_spin.setProperty("aiControl", True)
        controls_layout.addWidget(QLabel("Höhe (Custom)", controls), 1, 2)
        controls_layout.addWidget(height_spin, 1, 3)

        max_spin = QSpinBox(controls)
        max_spin.setRange(1, 4)
        max_spin.setValue(1)
        self._ai_max_images_spin = max_spin
        max_spin.setProperty("aiControl", True)
        controls_layout.addWidget(QLabel("Anzahl Bilder", controls), 2, 0)
        controls_layout.addWidget(max_spin, 2, 1)

        enhance_check = QCheckBox("Prompt verbessern", controls)
        enhance_check.setChecked(True)
        enhance_check.setObjectName("AISeedreamEnhance")
        self._ai_enhance_check = enhance_check
        controls_layout.addWidget(enhance_check, 2, 2, 1, 2)

        generate_button = QPushButton("Seedream Bild generieren", controls)
        generate_button.setObjectName("AISeedreamGenerateButton")
        generate_button.setCursor(Qt.CursorShape.PointingHandCursor)
        generate_button.setStyleSheet(
            """
            QPushButton#AISeedreamGenerateButton {
                border: none;
                border-radius: 12px;
                padding: 10px 16px;
                font-weight: 600;
                color: #f8fafc;
                background-color: #3b82f6;
            }
            QPushButton#AISeedreamGenerateButton:hover {
                background-color: #60a5fa;
            }
            QPushButton#AISeedreamGenerateButton:pressed {
                background-color: #2563eb;
            }
            QPushButton#AISeedreamGenerateButton:disabled {
                background-color: rgba(59, 130, 246, 0.3);
                color: rgba(248, 250, 252, 0.6);
            }
            """
        )
        generate_button.clicked.connect(self._handle_ai_generate_clicked)
        self._ai_generate_button = generate_button
        controls_layout.addWidget(generate_button, 3, 0, 1, 4)
        controls_layout.setRowStretch(4, 1)

        layout.addWidget(controls)

        status_label = QLabel("Bereit.", view)
        status_label.setObjectName("AISeedreamStatus")
        status_label.setContentsMargins(12, 4, 12, 8)
        status_label.setStyleSheet(
            """
            QLabel#AISeedreamStatus {
                color: rgba(255, 255, 255, 0.75);
                font-size: 12px;
                letter-spacing: 0.3px;
            }
            """
        )
        self._ai_status_label = status_label
        layout.addWidget(status_label)

        gallery = ReplicateGalleryWidget(view, show_labels=False, thumbnail=QSize(160, 160))
        gallery.setIconSize(QSize(160, 160))
        gallery.entryActivated.connect(self._handle_ai_gallery_entry_activated)
        self._ai_gallery = gallery
        layout.addWidget(gallery, 1)
        return view

    # ------------------------------------------------------------------ #
    # Drawer
    # ------------------------------------------------------------------ #
    def _build_ai_drawer(self, parent: QWidget) -> QWidget:
        drawer = QFrame(parent)
        drawer.setObjectName("AISeedreamDrawer")
        drawer.setMinimumWidth(44)
        drawer.setMaximumWidth(self._ai_drawer_thumb.width() + 20)
        drawer_layout = QVBoxLayout(drawer)
        drawer_layout.setContentsMargins(6, 6, 6, 6)
        drawer_layout.setSpacing(6)
        drawer.setStyleSheet(
            """
            QFrame#AISeedreamDrawer {
                background-color: rgba(0, 0, 0, 0.45);
                border-left: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
            }
            """
        )

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(6)
        header.addStretch(1)

        toggle = QToolButton(drawer)
        toggle.setCheckable(True)
        toggle.setChecked(False)
        toggle.setIcon(QIcon(str(ACTION_ICONS["drawer_close"])))
        toggle.clicked.connect(self._handle_ai_drawer_toggled)
        toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        toggle.setObjectName("AISeedreamDrawerToggle")
        toggle.setFixedSize(28, 28)
        toggle.setStyleSheet(
            """
            QToolButton#AISeedreamDrawerToggle {
                border: none;
                border-radius: 6px;
                background-color: rgba(255, 255, 255, 0.08);
                padding: 4px;
            }
            QToolButton#AISeedreamDrawerToggle:hover {
                background-color: rgba(255, 255, 255, 0.18);
            }
            QToolButton#AISeedreamDrawerToggle:pressed {
                background-color: rgba(255, 255, 255, 0.28);
            }
            """
        )
        self._ai_drawer_toggle = toggle
        header.addWidget(toggle, 0, Qt.AlignmentFlag.AlignRight)
        drawer_layout.addLayout(header)

        gallery = ReplicateGalleryWidget(
            drawer,
            show_labels=False,
            vertical=True,
            thumbnail=self._ai_drawer_thumb,
        )
        gallery.setThumbnailSize(self._ai_drawer_thumb)
        gallery.entryActivated.connect(self._handle_ai_gallery_entry_activated)
        self._ai_drawer_gallery = gallery
        drawer_layout.addWidget(gallery, 1)

        self._ai_drawer = drawer
        self._handle_ai_drawer_toggled(False)
        return drawer

    def _handle_ai_drawer_toggled(self, checked: bool) -> None:
        drawer = self._ai_drawer
        toggle = self._ai_drawer_toggle
        gallery = self._ai_drawer_gallery
        if drawer is None or toggle is None or gallery is None:
            return
        if checked:
            toggle.setIcon(QIcon(str(ACTION_ICONS["drawer_close"])))
            width = self._ai_drawer_thumb.width() + 20
            drawer.setMaximumWidth(width)
            drawer.setMinimumWidth(width)
            gallery.show()
        else:
            toggle.setIcon(QIcon(str(ACTION_ICONS["drawer_open"])))
            drawer.setMaximumWidth(44)
            drawer.setMinimumWidth(44)
            gallery.hide()

    # ------------------------------------------------------------------ #
    # Handlers
    # ------------------------------------------------------------------ #
    def _handle_ai_size_mode_changed(self) -> None:
        custom = self._ai_size_combo is not None and self._ai_size_combo.currentData() == "custom"
        if self._ai_width_spin:
            self._ai_width_spin.setEnabled(custom)
        if self._ai_height_spin:
            self._ai_height_spin.setEnabled(custom)

    def _handle_ai_generate_clicked(self) -> None:
        service = self._replicate_service
        if service is None:
            QMessageBox.warning(self, "Replicate", "Der Replicate-Dienst steht nicht zur Verfügung.")
            return
        if not self._ensure_replicate_api_token():
            return
        if not self._ai_prompt_input:
            return
        prompt = self._ai_prompt_input.toPlainText().strip()
        if not prompt:
            QMessageBox.information(self, "Seedream", "Bitte zuerst einen Prompt eingeben.")
            return
        try:
            size = self._ai_size_combo.currentData() if self._ai_size_combo else "2K"
            aspect = self._ai_aspect_combo.currentData() if self._ai_aspect_combo else "match_input_image"
            width = self._ai_width_spin.value() if self._ai_width_spin else 2048
            height = self._ai_height_spin.value() if self._ai_height_spin else 2048
            enhance = self._ai_enhance_check.isChecked() if self._ai_enhance_check else True
            max_images = self._ai_max_images_spin.value() if self._ai_max_images_spin else 1
            request_id = service.generate_seedream(
                prompt=prompt,
                aspect_ratio=aspect,
                size=size,
                width=width,
                height=height,
                enhance_prompt=enhance,
                max_images=max_images,
                image_inputs=[],
            )
        except Exception as exc:
            QMessageBox.warning(self, "Seedream", str(exc))
            return
        self._ai_request_meta[request_id] = {
            "prompt": prompt,
            "aspect_ratio": aspect,
            "size": size,
            "width": width,
            "height": height,
            "enhance_prompt": enhance,
            "max_images": max_images,
        }
        self._set_ai_status("Generierung wird vorbereitet …")
        self._apply_ai_busy_state(True)

    def _handle_ai_generation_started(self, request_id: str) -> None:
        self._set_ai_status("Seedream 4 gestartet …")
        self._ai_request_meta.setdefault(request_id, {})

    def _handle_ai_generation_progress(self, message: str) -> None:
        self._set_ai_status(message)

    def _handle_ai_generation_failed(self, request_id: str, message: str) -> None:
        self._apply_ai_busy_state(False)
        self._set_ai_status("Fehler bei der Generierung.")
        QMessageBox.warning(self, "Seedream", message)
        self._ai_request_meta.pop(request_id, None)

    def _handle_ai_generation_finished(self, request_id: str, temp_paths: list[str]) -> None:
        meta = self._ai_request_meta.pop(request_id, {"prompt": ""})
        prompt = meta.get("prompt") or "Seedream"
        saved = 0
        for path in temp_paths:
            stored = ""
            try:
                stored = self._viewmodel.import_replicate_asset(path)
                self._viewmodel.add_replicate_entry(stored, prompt=prompt, metadata=meta)
                saved += 1
            except Exception as exc:
                QMessageBox.warning(self, "Seedream", f"Ausgabe konnte nicht gespeichert werden: {exc}")
            finally:
                Path(path).unlink(missing_ok=True)
        self._apply_ai_busy_state(False)
        self._set_ai_status(f"Fertig. {saved} Bild(er) gespeichert.")
        self._refresh_ai_galleries()

    def _handle_ai_gallery_entry_activated(self, entry_id: str) -> None:
        entry = self._viewmodel.get_replicate_entry(entry_id)
        if not entry:
            return
        prompt = entry.get("prompt") or "Seedream"
        QMessageBox.information(self, "Seedream-Prompt", prompt)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _set_ai_status(self, message: str) -> None:
        if self._ai_status_label is not None:
            self._ai_status_label.setText(message)

    def _apply_ai_busy_state(self, busy: bool) -> None:
        if self._ai_generate_button is not None:
            self._ai_generate_button.setEnabled(not busy)

    def _refresh_ai_galleries(self) -> None:
        entries = self._viewmodel.replicate_entries()

        def resolver(path: str) -> str:
            return str(self._project_service.resolve_asset_path(path))
        if self._ai_gallery is not None:
            self._ai_gallery.set_entries(entries, resolver)
        if self._ai_drawer_gallery is not None:
            self._ai_drawer_gallery.set_entries(entries, resolver)

    def _ensure_replicate_api_token(self) -> bool:
        service = self._replicate_service
        if service is None:
            return False
        if service.has_api_token():
            return True
        token, ok = QInputDialog.getText(
            self,
            "Replicate API-Key",
            "Bitte Replicate API-Key eingeben:",
            QLineEdit.EchoMode.Password,
        )
        if not ok or not token.strip():
            return False
        service.set_api_token(token.strip())
        return service.has_api_token()
