from __future__ import annotations

from pathlib import Path

from slidequest.services.storage import PROJECT_ROOT

STATUS_BAR_SIZE = 48
SYMBOL_BUTTON_SIZE = STATUS_BAR_SIZE - 8
STATUS_ICON_SIZE = STATUS_BAR_SIZE - 12
ICON_PIXMAP_SIZE = 24
EXPLORER_HEADER_HEIGHT = 60
EXPLORER_FOOTER_HEIGHT = EXPLORER_HEADER_HEIGHT
DETAIL_HEADER_HEIGHT = 60
DETAIL_FOOTER_HEIGHT = DETAIL_HEADER_HEIGHT


class ButtonSpec:
    def __init__(
        self,
        name: str,
        icon: Path,
        tooltip: str,
        *,
        checkable: bool = False,
        auto_exclusive: bool = False,
        accent_on_checked: bool = False,
        checked_icon: Path | None = None,
        checked_by_default: bool = False,
    ) -> None:
        self.name = name
        self.icon = icon
        self.tooltip = tooltip
        self.checkable = checkable
        self.auto_exclusive = auto_exclusive
        self.accent_on_checked = accent_on_checked
        self.checked_icon = checked_icon
        self.checked_by_default = checked_by_default


SYMBOL_BUTTON_SPECS: tuple[ButtonSpec, ...] = (
    ButtonSpec(
        "LayoutExplorerLauncher",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "layouts" / "columns-gap.svg",
        "Layoutübersicht öffnen",
        checkable=True,
        auto_exclusive=True,
        checked_by_default=True,
    ),
    ButtonSpec(
        "AudioExplorerLauncher",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "audio" / "volume-up.svg",
        "Audio-Einstellungen öffnen",
        checkable=True,
        auto_exclusive=True,
    ),
    ButtonSpec(
        "NoteExplorerLauncher",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "files" / "file-earmark.svg",
        "Notizübersicht öffnen",
        checkable=True,
        auto_exclusive=True,
    ),
    ButtonSpec(
        "FileExplorerLauncher",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "files" / "folder.svg",
        "Dateiexplorer öffnen",
        checkable=True,
        auto_exclusive=True,
    ),
)

PRESENTATION_BUTTON_SPEC = ButtonSpec(
    "PresentationToggleButton",
    PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "window" / "window-fullscreen.svg",
    "Präsentationsfenster anzeigen",
)

STATUS_BUTTON_SPECS: tuple[ButtonSpec, ...] = (
    ButtonSpec(
        "StatusShuffleButton",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "audio" / "shuffle.svg",
        "Shuffle aktivieren",
        checkable=True,
        accent_on_checked=True,
    ),
    ButtonSpec(
        "StatusPreviousTrackButton",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "audio" / "skip-backward-fill.svg",
        "Vorheriger Titel",
    ),
    ButtonSpec(
        "StatusPlayPauseButton",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "audio" / "play-fill.svg",
        "Play/Pause",
        checkable=True,
        accent_on_checked=True,
        checked_icon=PROJECT_ROOT
        / "assets"
        / "icons"
        / "bootstrap"
        / "audio"
        / "pause-fill.svg",
    ),
    ButtonSpec(
        "StatusStopButton",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "audio" / "stop-fill.svg",
        "Stopp",
    ),
    ButtonSpec(
        "StatusNextTrackButton",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "audio" / "skip-forward-fill.svg",
        "Nächster Titel",
    ),
    ButtonSpec(
        "StatusLoopButton",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "audio" / "repeat.svg",
        "Loop aktivieren",
        checkable=True,
        accent_on_checked=True,
        checked_by_default=True,
    ),
    ButtonSpec(
        "StatusMuteButton",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "audio" / "volume-mute.svg",
        "Stummschalten",
        checkable=True,
        accent_on_checked=True,
    ),
    ButtonSpec(
        "StatusVolumeDownButton",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "audio" / "volume-down.svg",
        "Leiser",
    ),
    ButtonSpec(
        "StatusVolumeUpButton",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "audio" / "volume-up.svg",
        "Lauter",
    ),
)

STATUS_VOLUME_BUTTONS = {
    "StatusMuteButton",
    "StatusVolumeDownButton",
    "StatusVolumeUpButton",
}

ACTION_ICONS = {
    "search": PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "actions" / "search.svg",
    "filter": PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "actions" / "filter.svg",
    "create": PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "actions" / "plus-square.svg",
    "edit": PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "actions" / "pencil-square.svg",
    "delete": PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "actions" / "trash.svg",
}

EXPLORER_CRUD_SPECS: tuple[ButtonSpec, ...] = (
    ButtonSpec("ExplorerCreateButton", ACTION_ICONS["create"], "Neuen Eintrag anlegen"),
    ButtonSpec("ExplorerDeleteButton", ACTION_ICONS["delete"], "Auswahl löschen"),
)

PLAYLIST_ITEM_ICONS = {
    "drag": PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "actions" / "grip-vertical.svg",
    "play": PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "audio" / "play-fill.svg",
    "stop": PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "audio" / "stop-fill.svg",
    "fade_in": PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "actions" / "sort-up.svg",
    "fade_out": PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "actions" / "sort-down.svg",
    "delete": ACTION_ICONS["delete"],
}

PLAYLIST_CONTROL_SPECS: tuple[ButtonSpec, ...] = (
    ButtonSpec(
        "PlaylistShuffleButton",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "audio" / "shuffle.svg",
        "Playlist zufällig abspielen",
        checkable=True,
        accent_on_checked=True,
    ),
    ButtonSpec(
        "PlaylistPreviousTrackButton",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "audio" / "skip-backward-fill.svg",
        "Vorheriger Playlist-Track",
    ),
    ButtonSpec(
        "PlaylistPlayPauseButton",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "audio" / "play-fill.svg",
        "Playlist Play/Pause",
        checkable=True,
        accent_on_checked=True,
        checked_icon=PROJECT_ROOT
        / "assets"
        / "icons"
        / "bootstrap"
        / "audio"
        / "pause-fill.svg",
    ),
    ButtonSpec(
        "PlaylistStopButton",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "audio" / "stop-fill.svg",
        "Playlist stoppen",
    ),
    ButtonSpec(
        "PlaylistNextTrackButton",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "audio" / "skip-forward-fill.svg",
        "Nächster Playlist-Track",
    ),
    ButtonSpec(
        "PlaylistLoopButton",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "audio" / "repeat.svg",
        "Playlist-Loop aktivieren",
        checkable=True,
        accent_on_checked=True,
        checked_by_default=True,
    ),
    ButtonSpec(
        "PlaylistMuteButton",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "audio" / "volume-mute.svg",
        "Playlist stummschalten",
        checkable=True,
        accent_on_checked=True,
    ),
    ButtonSpec(
        "PlaylistVolumeDownButton",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "audio" / "volume-down.svg",
        "Playlist leiser",
    ),
    ButtonSpec(
        "PlaylistVolumeUpButton",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "audio" / "volume-up.svg",
        "Playlist lauter",
    ),
)

PLAYLIST_VOLUME_BUTTONS = {
    "PlaylistMuteButton",
    "PlaylistVolumeDownButton",
    "PlaylistVolumeUpButton",
}
