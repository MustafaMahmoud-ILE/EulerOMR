"""SoundManager: plays specific WAV files for different events."""
import os
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import QUrl


class SoundManager:
    _active_players = []

    @classmethod
    def _play_sound(cls, filename: str):
        # Path relative to project root
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        sound_path = os.path.abspath(os.path.join(base_dir, "assets", "sounds", filename))
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
