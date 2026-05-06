"""PDF-to-image conversion; corner-mark detection; OMR bubble reader; auto-contrast adjuster."""

from __future__ import annotations

import math
import concurrent.futures
import multiprocessing
from typing import Callable

import cv2
import numpy as np
import pypdfium2 as pdfium
import structlog

from euler_omr.constants import (
    SCAN_DPI, FILL_THRESHOLD, AUTO_CONTRAST_ISSUE_THRESHOLD,
    VERSION_LETTERS, OPTION_LETTERS,
)
from euler_omr.models.scan_result import ScanResult, Issue, IssueType, PageState

logger = structlog.get_logger(__name__)


class ScanReadError(Exception):
    """Raised when scan reading fails."""
    pass


def _process_page_worker(pdf_path, page_idx, reader_config):
    # Reconstruct ScanReader in worker process
    from euler_omr.core.scan_reader import ScanReader
    reader = ScanReader(*reader_config)
    
    img = reader.load_pdf_page(pdf_path, page_idx)
    logs = []
    def log_collector(msg, level):
        logs.append((msg, level))
    
    result = reader.read_page(img, page_no=page_idx + 1, log_callback=log_collector)
    return result, logs

class ScanReader:
    """Reads scanned OMR sheets from a PDF file."""

    def __init__(
        self,
        id_digits: int,
        num_versions: int,
        active_questions: int,
        active_options: int,
        active_versions: int,
        num_questions: int = None,
    ):
        self.id_digits = id_digits
        self.num_versions = num_versions
        self.active_questions = active_questions
        self.active_options = active_options
        self.active_versions = active_versions
        self.num_questions = num_questions if num_questions is not None else active_questions

    def _get_config_tuple(self):
        return (
            self.id_digits,
            self.num_versions,
            self.active_questions,
            self.active_options,
            self.active_versions,
            self.num_questions
        )

    @staticmethod
    def load_pdf_pages(pdf_path: str) -> list[np.ndarray]:
        """Load all pages from a PDF as numpy arrays at SCAN_DPI."""
        doc = pdfium.PdfDocument(pdf_path)
        pages = []
        for i in range(len(doc)):
            page = doc[i]
            bitmap = page.render(scale=SCAN_DPI / 72.0)
            img = bitmap.to_numpy()
            # Convert from RGBA/RGB to BGR for OpenCV
            if img.shape[2] == 4:
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
            elif img.shape[2] == 3:
                img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            pages.append(img)
        doc.close()
        return pages

    @staticmethod
    def load_pdf_page(pdf_path: str, page_idx: int) -> np.ndarray:
        """Load a single page from a PDF as a numpy array."""
        doc = pdfium.PdfDocument(pdf_path)
        page = doc[page_idx]
        bitmap = page.render(scale=SCAN_DPI / 72.0)
        img = bitmap.to_numpy()
        if img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
        elif img.shape[2] == 3:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        doc.close()
        return img

    @staticmethod
    def get_pdf_page_count(pdf_path: str) -> int:
        """Return the number of pages in a PDF."""
        doc = pdfium.PdfDocument(pdf_path)
        count = len(doc)
        doc.close()
        return count

    @staticmethod
    def _find_corner_marks(gray: np.ndarray) -> list[tuple[int, int, int, int]] | None:
        """
        Find the four corner marks in a grayscale image.
        Returns list of (x, y, w, h) sorted by position, or None if not found.
        """
        _, binary = cv2.threshold(gray, 60, 255, cv2.THRESH_BINARY_INV)

        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Filter for rectangular contours of appropriate size
        h_img, w_img = gray.shape
        min_area = (h_img * w_img) * 0.0005  # Minimum area threshold
        max_area = (h_img * w_img) * 0.01    # Maximum area threshold

        rects = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            area = w * h
            if min_area < area < max_area:
                aspect = w / h if h > 0 else 0
                # Corner marks should be roughly rectangular
                if 0.3 < aspect < 5.0:
                    rects.append((x, y, w, h))

        if len(rects) < 4:
            return None

        # Sort by distance from corners to identify the four corner marks
        corners = [
            (0, 0),          # top-left
            (w_img, 0),      # top-right
            (0, h_img),      # bottom-left
            (w_img, h_img),  # bottom-right
        ]

        selected = []
        used_rects = set()
        for cx, cy in corners:
            best = None
            best_dist = float("inf")
            for rect in rects:
                if rect in used_rects:
                    continue
                rx, ry, rw, rh = rect
                center_x = rx + rw / 2
                center_y = ry + rh / 2
                dist = math.sqrt((center_x - cx) ** 2 + (center_y - cy) ** 2)
                if dist < best_dist:
                    best_dist = dist
                    best = rect
            if best and best_dist < max(h_img, w_img) * 0.2:
                selected.append(best)
                used_rects.add(best)

        if len(selected) != 4:
            return None

        return selected

    @staticmethod
    def _detect_orientation(marks: list[tuple[int, int, int, int]]) -> int:
        """
        Determine rotation needed based on the wider top-left corner mark.
        Returns rotation in degrees (0, 90, 180, 270).
        """
        # The widest mark should be at top-left
        widest_idx = max(range(len(marks)), key=lambda i: marks[i][2])

        # marks are in order: TL, TR, BL, BR
        if widest_idx == 0:
            return 0    # Already correct
        elif widest_idx == 1:
            return 270  # Rotated 90° clockwise -> need 270° correction
        elif widest_idx == 3:
            return 180  # Upside down
        else:  # widest_idx == 2
            return 90   # Rotated 270° clockwise -> need 90° correction

    @staticmethod
    def _rotate_image(img: np.ndarray, degrees: int) -> np.ndarray:
        """Rotate image by 0, 90, 180, or 270 degrees."""
        if degrees == 0:
            return img
        elif degrees == 90:
            return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        elif degrees == 180:
            return cv2.rotate(img, cv2.ROTATE_180)
        elif degrees == 270:
            return cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
        return img

    @staticmethod
    def _perspective_correct(gray: np.ndarray, marks: list[tuple[int, int, int, int]]) -> np.ndarray:
        """Apply perspective correction using corner mark centroids."""
        h, w = gray.shape[:2]

        # Get precise centroids of the four marks using image moments
        src_points = []
        for x, y, mw, mh in marks:
            y1, y2 = max(0, int(y)), min(h, int(y + mh))
            x1, x2 = max(0, int(x)), min(w, int(x + mw))
            roi = gray[y1:y2, x1:x2]
            if len(roi.shape) == 3 and roi.shape[2] == 3:
                roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            _, roi_bin = cv2.threshold(roi, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            M_mom = cv2.moments(roi_bin)
            if M_mom["m00"] > 0:
                cx = x1 + M_mom["m10"] / M_mom["m00"]
                cy = y1 + M_mom["m01"] / M_mom["m00"]
            else:
                cx = x + mw / 2.0
                cy = y + mh / 2.0
            src_points.append([cx, cy])
        src = np.float32(src_points)

        # Define destination points (ideal LaTeX centroids at 200 DPI)
        dst = np.float32([
            [173.0, 126.0],     # top-left
            [1527.5, 126.0],    # top-right
            [126.0, 2212.5],    # bottom-left
            [1527.5, 2212.5],   # bottom-right
        ])

        M = cv2.getPerspectiveTransform(src, dst)
        corrected = cv2.warpPerspective(gray, M, (w, h), borderValue=255)
        return corrected

    def _read_bubbles_in_region(
        self,
        gray: np.ndarray,
        x_start: int, y_start: int,
        cols: int, rows: int,
        x_step: float, y_step: float,
        radius: int,
    ) -> list[list[float]]:
        """
        Read fill ratios for a grid of bubbles.
        Returns a 2D array [col][row] of fill ratios (0.0 = empty, 1.0 = full).
        """
        h, w = gray.shape
        results = []
        for c in range(cols):
            col_ratios = []
            for r in range(rows):
                cx = int(x_start + c * x_step)
                cy = int(y_start + r * y_step)
                # Ensure we're within bounds
                cx = max(radius, min(w - radius - 1, cx))
                cy = max(radius, min(h - radius - 1, cy))
                # Extract circular region
                mask = np.zeros((2 * radius + 1, 2 * radius + 1), dtype=np.uint8)
                cv2.circle(mask, (radius, radius), radius, 255, -1)
                roi = gray[cy - radius:cy + radius + 1, cx - radius:cx + radius + 1]
                if roi.shape[0] != mask.shape[0] or roi.shape[1] != mask.shape[1]:
                    col_ratios.append(1.0)  # Treat out-of-bounds as empty
                    continue
                masked = cv2.bitwise_and(roi, roi, mask=mask)
                # Invert so filled bubbles have high values
                inv = 255 - masked
                total_pixels = cv2.countNonZero(mask)
                filled_pixels = cv2.countNonZero(cv2.bitwise_and(inv, inv, mask=mask))
                ratio = filled_pixels / total_pixels if total_pixels > 0 else 0.0
                col_ratios.append(ratio)
            results.append(col_ratios)
        return results

    def read_page(
        self,
        img: np.ndarray,
        page_no: int,
        log_callback: Callable | None = None,
        is_fallback: bool = False,
    ) -> ScanResult:
        """
        Read a single scanned page and return a ScanResult.
        """
        _log = log_callback or (lambda msg, level: None)
        log = logger.bind(page_no=page_no)

        result = ScanResult(page_no=page_no)
        issues: list[Issue] = []

        # Convert to grayscale
        if len(img.shape) == 3 and img.shape[2] == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        elif len(img.shape) == 3 and img.shape[2] == 1:
            gray = img[:, :, 0].copy()
        else:
            gray = img.copy()

        h, w = gray.shape

        # Try to find corner marks
        marks = self._find_corner_marks(gray)
        if marks is not None:
            # Check orientation
            rotation = self._detect_orientation(marks)
            if rotation != 0:
                gray = self._rotate_image(gray, rotation)
                img = self._rotate_image(img, rotation)
                h, w = gray.shape
                marks = self._find_corner_marks(gray)
                _log(f"Page {page_no}: Corrected orientation by {rotation} degrees", "INFO")

            if marks is not None:
                gray = self._perspective_correct(gray, marks)
                _log(f"Page {page_no}: Applied perspective correction", "DEBUG")
        else:
            _log(f"Page {page_no}: Corner marks not found; proceeding without correction", "WARNING")

        # Apply adaptive threshold for bubble reading
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Dilation helps connect "zigzag" or "scribble" marks into a solid fill
        # This makes the reader much more robust against messy student marking.
        kernel = np.ones((3, 3), np.uint8)
        binary = cv2.dilate(binary, kernel, iterations=1)

        # Use normalized threshold from constants
        threshold = FILL_THRESHOLD / 255.0  # e.g., 128/255 approx 0.5
        # Actually, let's keep it a bit more sensitive (0.3 is good for scribbles)
        # but let's use the constant if it's set specifically.
        # For now, let's stick to 0.3 as the base but use the constant's "intent"
        final_threshold = min(0.3, threshold)

        # Estimate bubble positions based on page geometry
        # These are approximate positions based on the LaTeX template at SCAN_DPI
        dpi_scale = SCAN_DPI / 72.0  # Points to pixels
        cm_to_px = SCAN_DPI / 2.54  # cm to pixels

        bubble_r_px = int(0.22 * cm_to_px)
        bubble_step_px = 0.6 * cm_to_px
        row_step_px = 0.5 * cm_to_px

        # --- Read Student ID bubbles ---
        # Fixed x of the last digit center (1496 pixels - 17)
        x_last_col_center = 1496 - 17
        id_x_start = int(x_last_col_center - (self.id_digits - 1) * bubble_step_px)
        id_y_start = 287

        # Store ID region for review UI
        result.crop_regions["id"] = {
            "x_start": int(max(0, id_x_start - 35)),
            "y_start": int(max(0, id_y_start - 30)),
            "x_end": int(min(w, x_last_col_center + 35)),
            "y_end": int(min(h, id_y_start + 9 * row_step_px + 30))
        }
        # Table region (Written data)
        result.crop_regions["table"] = {"x_start": 157, "y_start": 433, "x_end": 805, "y_end": 688}

        student_id = ""
        for digit_col in range(self.id_digits):
            x = int(id_x_start + digit_col * bubble_step_px)
            best_digit = -1
            best_ratio = 0.0
            filled_count = 0

            for digit_val in range(10):
                y = int(id_y_start + digit_val * row_step_px)
                # Read fill ratio at this position
                cx = max(bubble_r_px, min(w - bubble_r_px - 1, x))
                cy = max(bubble_r_px, min(h - bubble_r_px - 1, y))

                mask = np.zeros((2 * bubble_r_px + 1, 2 * bubble_r_px + 1), dtype=np.uint8)
                cv2.circle(mask, (bubble_r_px, bubble_r_px), bubble_r_px, 255, -1)

                y1, y2 = cy - bubble_r_px, cy + bubble_r_px + 1
                x1, x2 = cx - bubble_r_px, cx + bubble_r_px + 1
                if y1 < 0 or x1 < 0 or y2 > h or x2 > w:
                    continue
                roi = binary[y1:y2, x1:x2]
                if roi.shape[0] != mask.shape[0] or roi.shape[1] != mask.shape[1]:
                    continue

                total = cv2.countNonZero(mask)
                filled = cv2.countNonZero(cv2.bitwise_and(roi, roi, mask=mask))
                ratio = filled / total if total > 0 else 0.0

                if ratio > final_threshold:
                    filled_count += 1
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_digit = digit_val

            if filled_count == 0:
                student_id += "*"
                issues.append(Issue(
                    issue_type=IssueType.MISSING_DIGIT,
                    field_name=f"id_digit_{digit_col}",
                    detail=f"No bubble filled in ID digit column {digit_col + 1}",
                ))
            elif filled_count > 1:
                student_id += "*"
                issues.append(Issue(
                    issue_type=IssueType.MULTI_DIGIT,
                    field_name=f"id_digit_{digit_col}",
                    detail=f"Multiple bubbles filled in ID digit column {digit_col + 1}",
                ))
            else:
                student_id += str(best_digit)

        result.student_id = student_id

        # --- Read Version bubble ---
        version_x_start = 176
        version_y = 778

        # Store Version region for review UI
        result.crop_regions["version"] = {
            "x_start": int(max(0, version_x_start - 35)),
            "y_start": int(max(0, version_y - 30)),
            "x_end": int(min(w, version_x_start + (self.active_versions - 1) * bubble_step_px + 35)),
            "y_end": int(min(h, version_y + 30))
        }

        best_version = -1
        best_ratio = 0.0
        version_filled = 0

        for v_idx in range(self.active_versions):
            x = int(version_x_start + v_idx * bubble_step_px)
            y = version_y
            cx = max(bubble_r_px, min(w - bubble_r_px - 1, x))
            cy = max(bubble_r_px, min(h - bubble_r_px - 1, y))

            mask = np.zeros((2 * bubble_r_px + 1, 2 * bubble_r_px + 1), dtype=np.uint8)
            cv2.circle(mask, (bubble_r_px, bubble_r_px), bubble_r_px, 255, -1)

            y1, y2 = cy - bubble_r_px, cy + bubble_r_px + 1
            x1, x2 = cx - bubble_r_px, cx + bubble_r_px + 1
            if y1 < 0 or x1 < 0 or y2 > h or x2 > w:
                continue
            roi = binary[y1:y2, x1:x2]
            if roi.shape[0] != mask.shape[0] or roi.shape[1] != mask.shape[1]:
                continue

            total = cv2.countNonZero(mask)
            filled = cv2.countNonZero(cv2.bitwise_and(roi, roi, mask=mask))
            ratio = filled / total if total > 0 else 0.0

            if ratio > final_threshold:
                version_filled += 1
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_version = v_idx

        if version_filled == 0:
            result.version = ""
            issues.append(Issue(
                issue_type=IssueType.MISSING_VERSION,
                field_name="version",
                detail="No version bubble filled",
            ))
        elif version_filled > 1:
            result.version = ""
            issues.append(Issue(
                issue_type=IssueType.MULTI_VERSION,
                field_name="version",
                detail="Multiple version bubbles filled",
            ))
        else:
            result.version = VERSION_LETTERS[best_version]

        # --- Read Question bubbles ---
        answers = []
        rows_per_col = math.ceil(self.num_questions / 3)
        q_y_start = 868.5
        q_x_starts = [204.5, 650.7, 1097.0]

        for q_idx in range(self.active_questions):
            col_idx = q_idx // rows_per_col
            row_idx = q_idx % rows_per_col

            if col_idx >= len(q_x_starts):
                answers.append("")
                continue

            base_x = q_x_starts[col_idx]
            y = int(q_y_start + row_idx * row_step_px)

            best_option = -1
            best_ratio = 0.0
            option_filled = 0

            for opt_idx in range(self.active_options):
                x = int(base_x + opt_idx * bubble_step_px)
                cx = max(bubble_r_px, min(w - bubble_r_px - 1, x))
                cy = max(bubble_r_px, min(h - bubble_r_px - 1, y))

                mask = np.zeros((2 * bubble_r_px + 1, 2 * bubble_r_px + 1), dtype=np.uint8)
                cv2.circle(mask, (bubble_r_px, bubble_r_px), bubble_r_px, 255, -1)

                y1, y2 = cy - bubble_r_px, cy + bubble_r_px + 1
                x1, x2 = cx - bubble_r_px, cx + bubble_r_px + 1
                if y1 < 0 or x1 < 0 or y2 > h or x2 > w:
                    continue
                roi = binary[y1:y2, x1:x2]
                if roi.shape[0] != mask.shape[0] or roi.shape[1] != mask.shape[1]:
                    continue

                total = cv2.countNonZero(mask)
                filled = cv2.countNonZero(cv2.bitwise_and(roi, roi, mask=mask))
                ratio = filled / total if total > 0 else 0.0

                if ratio > final_threshold:
                    option_filled += 1
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_option = opt_idx

            if option_filled == 0:
                answers.append("")
                issues.append(Issue(
                    issue_type=IssueType.MISSING_ANSWER,
                    field_name=f"q_{q_idx + 1}",
                    detail=f"No option filled for question {q_idx + 1}",
                ))
            elif option_filled > 1:
                answers.append("")
                issues.append(Issue(
                    issue_type=IssueType.MULTI_ANSWER,
                    field_name=f"q_{q_idx + 1}",
                    detail=f"Multiple options filled for question {q_idx + 1}",
                ))
            else:
                answers.append(OPTION_LETTERS[best_option])

            # Store Question region for review UI
            result.crop_regions[str(q_idx)] = {
                "x_start": int(max(0, base_x - 35)),
                "y_start": int(max(0, y - 22)),
                "x_end": int(min(w, base_x + (self.active_options - 1) * bubble_step_px + 35)),
                "y_end": int(min(h, y + 22))
            }

        result.answers = answers
        result.issues = issues

        # Auto-contrast fallback if too many issues
        if not is_fallback and len(issues) > AUTO_CONTRAST_ISSUE_THRESHOLD:
            _log(f"Page {page_no}: {len(issues)} issues detected, attempting auto-contrast...", "WARNING")
            # Try CLAHE
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            alt_result = self.read_page(enhanced, page_no, log_callback=None, is_fallback=True)
            if len(alt_result.issues) < len(issues):
                _log(f"Page {page_no}: Auto-contrast reduced issues from {len(issues)} to {len(alt_result.issues)}", "INFO")
                result = alt_result

        # Update state
        if result.issues:
            result.state = PageState.NEEDS_REVIEW
        else:
            result.state = PageState.SUCCESS

        _log(f"Page {page_no}: state={result.state.value}, issues={len(result.issues)}", "INFO")
        return result

    def read_pdf(
        self,
        pdf_path: str,
        progress_callback: Callable[[int, int], None] | None = None,
        log_callback: Callable[[str, str], None] | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> list[ScanResult]:
        """Read all pages from a PDF and return scan results using multiprocessing."""
        page_count = self.get_pdf_page_count(pdf_path)
        results = [None] * page_count
        
        # Use ProcessPoolExecutor for parallel processing
        num_workers = min(multiprocessing.cpu_count(), 8)
        config = self._get_config_tuple()
        
        with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
            future_to_page = {
                executor.submit(_process_page_worker, pdf_path, i, config): i 
                for i in range(page_count)
            }
            
            completed = 0
            for future in concurrent.futures.as_completed(future_to_page):
                if cancel_check and cancel_check():
                    executor.shutdown(wait=False, cancel_futures=True)
                    break
                    
                page_idx = future_to_page[future]
                try:
                    result, logs = future.result()
                    results[page_idx] = result
                    
                    if log_callback:
                        for msg, level in logs:
                            log_callback(msg, level)
                            
                except Exception as e:
                    if log_callback:
                        log_callback(f"Error processing page {page_idx + 1}: {e}", "ERROR")
                
                completed += 1
                if progress_callback:
                    progress_callback(completed, page_count)
        
        return [r for r in results if r is not None]
