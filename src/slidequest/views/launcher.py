from __future__ import annotations

from PySide6.QtCore import Qt, QElapsedTimer, QTimer
from PySide6.QtGui import QPixmap, QTransform
from PySide6.QtWidgets import QLabel, QStackedLayout, QVBoxLayout, QWidget

from slidequest.services.storage import PROJECT_ROOT
from slidequest.ui.constants import ACTION_ICONS


class LauncherWindow(QWidget):
    def __init__(self) -> None:
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setObjectName("LauncherWindow")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setFixedSize(360, 360)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        stack_container = QWidget(self)
        stack_container.setFixedSize(220, 220)
        stack = QStackedLayout(stack_container)
        stack.setContentsMargins(0, 0, 0, 0)
        stack.setStackingMode(QStackedLayout.StackingMode.StackAll)

        logo_label = QLabel(stack_container)
        logo_path = PROJECT_ROOT / "assets" / "others" / "SlideQuestLogo_large.png"
        if not logo_path.exists():
            logo_path = PROJECT_ROOT / "assets" / "others" / "SlideQuestLogo.png"
        logo_pix = QPixmap(str(logo_path))
        logo_label.setPixmap(logo_pix.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        spinner_label = _SpinnerLabel(stack_container)
        spinner_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        spinner_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        stack.addWidget(logo_label)
        stack.addWidget(spinner_label)

        layout.addWidget(stack_container, alignment=Qt.AlignmentFlag.AlignCenter)
        self._timer = QElapsedTimer()
        self._timer.start()

    def elapsed(self) -> int:
        return int(self._timer.elapsed())


class _SpinnerLabel(QLabel):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        source = ACTION_ICONS.get("spinner")
        pixmap = QPixmap(str(source)) if source and source.exists() else QPixmap()
        if pixmap.isNull():
            pixmap = QPixmap(48, 48)
            pixmap.fill(Qt.GlobalColor.transparent)
        colorized = pixmap
        self._base = colorized.scaled(54, 54, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self._angle = 0.0
        self.setPixmap(self._base)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance)
        self._timer.start(32)

    def _advance(self) -> None:
        self._angle = (self._angle + 6.0) % 360.0
        transform = QTransform().rotate(self._angle)
        rotated = self._base.transformed(transform, Qt.TransformationMode.SmoothTransformation)
        self.setPixmap(rotated)
