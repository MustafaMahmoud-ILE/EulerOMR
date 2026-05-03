"""Tests for scan_reader module."""
import pytest
import numpy as np
from euler_omr.core.scan_reader import ScanReader


class TestScanReader:
    def test_init(self):
        reader = ScanReader(
            id_digits=10, num_versions=4,
            active_questions=60, active_options=4, active_versions=4,
        )
        assert reader.id_digits == 10
        assert reader.active_questions == 60

    def test_find_corner_marks_blank(self):
        # White image should find no marks
        img = np.ones((800, 600), dtype=np.uint8) * 255
        marks = ScanReader._find_corner_marks(img)
        assert marks is None

    def test_rotate_image_identity(self):
        img = np.zeros((100, 200), dtype=np.uint8)
        rotated = ScanReader._rotate_image(img, 0)
        assert rotated.shape == (100, 200)

    def test_rotate_image_90(self):
        img = np.zeros((100, 200), dtype=np.uint8)
        rotated = ScanReader._rotate_image(img, 90)
        assert rotated.shape == (200, 100)

    def test_rotate_image_180(self):
        img = np.zeros((100, 200), dtype=np.uint8)
        rotated = ScanReader._rotate_image(img, 180)
        assert rotated.shape == (100, 200)
