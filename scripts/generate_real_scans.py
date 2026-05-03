"""
Python script to generate realistic scanned OMR pages from Data.xlsx in experiment folder.
"""
import os
import random
import math
import openpyxl
import cv2
import numpy as np
import fitz
import base64
import json
from PIL import Image

VERSION_LETTERS = [chr(65 + i) for i in range(26)]
OPTION_LETTERS = ["A", "B", "C", "D", "E", "F", "G", "H"]


def main():
    xlsx_path = "experiment/Data.xlsx"
    template_pdf = "experiment/TEMPLATE.pdf"
    eomrt_path = "experiment/EUI.eomrt"
    output_pdf = "experiment/RealScans.pdf"

    if not os.path.exists(xlsx_path):
        print(f"Error: {xlsx_path} not found.")
        return
    if not os.path.exists(template_pdf):
        print(f"Error: {template_pdf} not found.")
        return

    # Load dynamic config if available
    if os.path.exists(eomrt_path):
        f = open(eomrt_path, 'rb').read()
        eomrt = json.loads(base64.b64decode(f))
        c = eomrt.get('config', {})
        id_digits = c.get('id_digits', 8)
        active_versions = c.get('num_versions', 10)
        active_questions = c.get('num_questions', 60)
        active_options = c.get('num_options', 4)
    else:
        id_digits = 8
        active_versions = 10
        active_questions = 60
        active_options = 4

    # 1. Load data from Data.xlsx
    wb = openpyxl.load_workbook(xlsx_path)
    sheet = wb.active
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        print("Error: Excel file is empty.")
        return

    header = [str(cell).strip() for cell in rows[0]]
    data_rows = rows[1:]

    # Parse column indexes
    try:
        id_col = header.index("Student ID")
        ver_col = header.index("Version")
    except ValueError as e:
        print(f"Error: Missing essential header column in Data.xlsx: {e}")
        return

    # Identify question columns
    q_cols = []
    for idx, h in enumerate(header):
        if h.startswith("Q") and h[1:].isdigit():
            q_cols.append((int(h[1:]), idx))
    q_cols.sort()

    print(f"Found {len(data_rows)} student rows, {len(q_cols)} question columns.")

    # Render template page to a high-res numpy image (200 DPI)
    doc = fitz.open(template_pdf)
    pix = doc[0].get_pixmap(dpi=200)
    w, h = pix.width, pix.height

    # Convert pixmap to numpy BGR image
    template_img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(h, w, 3)
    template_img = cv2.cvtColor(template_img, cv2.COLOR_RGB2BGR)

    # Coordinates and sizes at 200 DPI
    cm_to_px = 200 / 2.54
    bubble_r_px = int(0.22 * cm_to_px)
    bubble_step_px = 0.6 * cm_to_px
    row_step_px = 0.5 * cm_to_px

    pil_pages = []

    for row_idx, r in enumerate(data_rows):
        img = template_img.copy()

        student_id = str(r[id_col]).strip() if r[id_col] is not None else ""
        version = str(r[ver_col]).strip() if r[ver_col] is not None else ""

        # --- Draw Student ID bubbles ---
        x_last_col_center = 1496 - 17
        id_x_start = int(x_last_col_center - (id_digits - 1) * bubble_step_px)
        id_y_start = 287

        padded_id = student_id.zfill(id_digits)[:id_digits]

        # 3% chance for a student ID issue
        has_id_issue = random.random() < 0.03
        id_issue_digit = random.randint(0, id_digits - 1) if has_id_issue else -1

        for digit_col in range(id_digits):
            x = int(id_x_start + digit_col * bubble_step_px)
            d_char = padded_id[digit_col]
            correct_val = int(d_char) if d_char.isdigit() else 0

            y = int(id_y_start + correct_val * row_step_px)
            cx = x + random.randint(-2, 2)
            cy = y + random.randint(-2, 2)
            cv2.circle(img, (cx, cy), bubble_r_px - 1, (0, 0, 0), -1)

            if digit_col == id_issue_digit:
                # Add another non-original mark with an X
                other_vals = [v for v in range(10) if v != correct_val]
                wrong_val = random.choice(other_vals)
                wy = int(id_y_start + wrong_val * row_step_px)
                wcx = x + random.randint(-2, 2)
                wcy = wy + random.randint(-2, 2)

                cv2.circle(img, (wcx, wcy), bubble_r_px - 1, (0, 0, 0), -1)
                # Draw X in white on it
                cv2.line(img, (wcx - 4, wcy - 4), (wcx + 4, wcy + 4), (255, 255, 255), 2)
                cv2.line(img, (wcx + 4, wcy - 4), (wcx - 4, wcy + 4), (255, 255, 255), 2)

        # --- Draw Version bubble ---
        version_x_start = 176
        version_y = 778

        # Map version letter to index
        correct_ver_idx = -1
        if version in VERSION_LETTERS:
            correct_ver_idx = VERSION_LETTERS.index(version)

        if correct_ver_idx != -1:
            x = int(version_x_start + correct_ver_idx * bubble_step_px)
            cx = x + random.randint(-2, 2)
            cy = version_y + random.randint(-2, 2)
            cv2.circle(img, (cx, cy), bubble_r_px - 1, (0, 0, 0), -1)

            # 3% chance for version issue
            if random.random() < 0.03:
                other_vers = [v for v in range(active_versions) if v != correct_ver_idx]
                if other_vers:
                    wrong_ver = random.choice(other_vers)
                    wx = int(version_x_start + wrong_ver * bubble_step_px)
                    wcx = wx + random.randint(-2, 2)
                    wcy = version_y + random.randint(-2, 2)

                    cv2.circle(img, (wcx, wcy), bubble_r_px - 1, (0, 0, 0), -1)
                    # Draw X in white
                    cv2.line(img, (wcx - 4, wcy - 4), (wcx + 4, wcy + 4), (255, 255, 255), 2)
                    cv2.line(img, (wcx + 4, wcy - 4), (wcx - 4, wcy + 4), (255, 255, 255), 2)

        # --- Draw Question bubbles ---
        rows_per_col = math.ceil(active_questions / 3)
        q_y_start = 868.5
        q_x_starts = [204.5, 650.7, 1097.0]

        for q_idx, (q_num, cell_idx) in enumerate(q_cols):
            if q_idx >= active_questions:
                break
            col_idx = q_idx // rows_per_col
            row_idx = q_idx % rows_per_col

            if col_idx >= len(q_x_starts):
                continue

            base_x = q_x_starts[col_idx]
            y = int(q_y_start + row_idx * row_step_px)

            ans = str(r[cell_idx]).strip() if r[cell_idx] is not None else ""
            correct_opt_idx = -1
            if ans and ans in OPTION_LETTERS[:active_options]:
                correct_opt_idx = OPTION_LETTERS.index(ans)

            if correct_opt_idx != -1:
                # 3% random error
                if random.random() < 0.03:
                    # Original answer
                    x = int(base_x + correct_opt_idx * bubble_step_px)
                    cx = x + random.randint(-2, 2)
                    cy = y + random.randint(-2, 2)
                    cv2.circle(img, (cx, cy), bubble_r_px - 1, (0, 0, 0), -1)

                    # Non-original answer crossed out with an X
                    other_opts = [idx for idx in range(active_options) if idx != correct_opt_idx]
                    if other_opts:
                        other_opt = random.choice(other_opts)
                        ox = int(base_x + other_opt * bubble_step_px)
                        ocx = ox + random.randint(-2, 2)
                        ocy = y + random.randint(-2, 2)

                        # Draw circle
                        cv2.circle(img, (ocx, ocy), bubble_r_px - 1, (0, 0, 0), -1)
                        # Draw X over it in white
                        cv2.line(img, (ocx - 4, ocy - 4), (ocx + 4, ocy + 4), (255, 255, 255), 2)
                        cv2.line(img, (ocx + 4, ocy - 4), (ocx - 4, ocy + 4), (255, 255, 255), 2)
                else:
                    x = int(base_x + correct_opt_idx * bubble_step_px)
                    cx = x + random.randint(-2, 2)
                    cy = y + random.randint(-2, 2)
                    cv2.circle(img, (cx, cy), bubble_r_px - 1, (0, 0, 0), -1)

        # Make the PDF look realistic
        angle = random.uniform(-1.2, 1.2)
        M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
        img = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))

        _, img_encoded = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
        pil_pages.append(img_encoded.tobytes())

    if pil_pages:
        out_doc = fitz.open()
        for img_bytes in pil_pages:
            page = out_doc.new_page(width=595, height=842)
            rect = fitz.Rect(0, 0, 595, 842)
            page.insert_image(rect, stream=img_bytes)
        out_doc.save(output_pdf)
        out_doc.close()
        print(f"Successfully generated {len(pil_pages)} realistic scan pages in: {output_pdf}")


if __name__ == "__main__":
    main()
