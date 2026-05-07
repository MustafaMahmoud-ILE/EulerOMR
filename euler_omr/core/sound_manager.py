"""SoundManager: plays specific WAV files for different events."""
import os
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import QUrl

from euler_omr.core.path_utils import get_asset_path


class SoundManager:
    _active_players = []

    @classmethod
    def _play_sound(cls, filename: str):
        # Path resolved via central utility
        sound_path = get_asset_path("sounds", filename)
        if os.path.exists(sound_path):
            player = QMediaPlayer()
            audio_output = QAudioOutput()
            player.setAudioOutput(audio_output)
            audio_output.setVolume(1.0)
            player.setSource(QUrl.fromLocalFile(sound_path))
            cls._active_players.append((player, audio_output))
            player.play()

            # Trim list to avoid leaks while keeping alive
            if len(cls._active_players) > 12:
                cls._active_players.pop(0)

    @classmethod
    def play_open(cls):
        cls._play_sound("open.wav")

    @classmethod
    def play_alert(cls):
        cls._play_sound("alerts.wav")

    @classmethod
    def play_click(cls):
        cls._play_sound("btnclicks.wav")

    @classmethod
    def play_complete(cls):
        cls._play_sound("complete.wav")
