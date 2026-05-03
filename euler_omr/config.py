"""Persistent QSettings wrapper for geometry, recents, and theme preferences."""

from PySide6.QtCore import QSettings
from euler_omr.constants import ORG_NAME, APP_NAME, MAX_RECENT_FILES


class AppConfig:
    """Wrapper around QSettings for persistent app configuration."""

    def __init__(self):
        self._settings = QSettings(ORG_NAME, APP_NAME)

    # --- Window Geometry ---
    def save_geometry(self, geometry: bytes):
        self._settings.setValue("window/geometry", geometry)

    def load_geometry(self) -> bytes | None:
        return self._settings.value("window/geometry")

    def save_state(self, state: bytes):
        self._settings.setValue("window/state", state)

    def load_state(self) -> bytes | None:
        return self._settings.value("window/state")

    # --- Splitter Sizes ---
    def save_splitter(self, name: str, sizes: list[int]):
        self._settings.setValue(f"splitters/{name}", sizes)

    def load_splitter(self, name: str) -> list[int] | None:
        val = self._settings.value(f"splitters/{name}")
        if val is not None:
            return [int(s) for s in val]
        return None

    # --- Recent Files ---
    def get_recents(self) -> list[str]:
        val = self._settings.value("recents/files", [])
        if isinstance(val, str):
            return [val] if val else []
        return list(val) if val else []

    def add_recent(self, path: str):
        recents = self.get_recents()
        if path in recents:
            recents.remove(path)
        recents.insert(0, path)
        recents = recents[:MAX_RECENT_FILES]
        self._settings.setValue("recents/files", recents)

    def remove_recent(self, path: str):
        recents = self.get_recents()
        if path in recents:
            recents.remove(path)
            self._settings.setValue("recents/files", recents)
