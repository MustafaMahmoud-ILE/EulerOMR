"""SoundManager: plays specific WAV files for different events."""
import os
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import QUrl

class SoundManager:
    _player = None
    _audio_output = None

    @classmethod
    def _play_sound(cls, filename: str):
        # Path relative to euler_omr/core/sound_manager.py: up two levels to euler_omr root, up one more to project root
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        sound_path = os.path.join(base_dir, "assets", "sounds", filename)
        if os.path.exists(sound_path):
            if cls._player is None:
                cls._player = QMediaPlayer()
                cls._audio_output = QAudioOutput()
                cls._player.setAudioOutput(cls._audio_output)
                cls._audio_output.setVolume(1.0)
            cls._player.setSource(QUrl.fromLocalFile(sound_path))
            cls._player.play()

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
