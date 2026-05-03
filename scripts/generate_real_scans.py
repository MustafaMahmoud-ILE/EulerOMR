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
from PIL import Image

VERSION_LETTERS = [chr(65 + i) for i in range(26)]
OPTION_LETTERS = ["A", "B", "C", "D", "E", "F", "G", "H"]


def main():
    xlsx_path = "experiment/Data.xlsx"
    template_pdf = "experiment/TEMPLATE.pdf"
    output_pdf = "experiment/RealScans.pdf"

    if not os.path.exists(xlsx_path):
        print(f"Error: {xlsx_path} not found.")
        return
    if not os.path.exists(template_pdf):
        print(f"Error: {template_pdf} not found.")
        return

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

    # Render template page to a high-res numpy image (150 DPI)
    doc = fitz.open(template_pdf)
    pix = doc[0].get_pixmap(dpi=150)
    w, h = pix.width, pix.height

    # Convert pixmap to numpy BGR image
    template_img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(h, w, 3)
    template_img = cv2.cvtColor(template_img, cv2.COLOR_RGB2BGR)

    # Coordinates and sizes at 150 DPI
    cm_to_px = 150 / 2.54
    bubble_r_px = int(0.22 * cm_to_px)
    bubble_step_px = 0.6 * cm_to_px
    row_step_px = 0.5 * cm_to_px

    id_digits = 8
    active_versions = 10
    active_questions = len(q_cols)
    active_options = 4

    pil_pages = []

    for row_idx, r in enumerate(data_rows):
        # Create a fresh copy of the template image for this student
        img = template_img.copy()

        student_id = str(r[id_col]).strip() if r[id_col] is not None else ""
        version = str(r[ver_col]).strip() if r[ver_col] is not None else ""

        # Make students commit random issues (e.g. 10% chance of an ID issue)
        make_id_issue = random.random() < 0.10
        make_ver_issue = random.random() < 0.10

        # --- Draw Student ID bubbles ---
        id_x_start = int(w * 0.55)
        id_y_start = int(h * 0.12)

        # Pad student_id with zeros or take first 8 digits
        padded_id = student_id.zfill(id_digits)[:id_digits]

        for digit_col in range(id_digits):
            x = int(id_x_start + digit_col * bubble_step_px)

            # Determine which digit bubble to fill
            d_char = padded_id[digit_col]
            correct_val = int(d_char) if d_char.isdigit() else 0

            # If simulating an issue for this digit:
            if make_id_issue and digit_col == random.randint(0, id_digits - 1):
                issue_type = random.choice(["missing", "multi"])
                if issue_type == "missing":
                    # Skip filling completely
                    continue
                elif issue_type == "multi":
                    # Fill correct bubble + random other bubble
                    other_val = (correct_val + 3) % 10
                    for v in [correct_val, other_val]:
                        y = int(id_y_start + v * row_step_px)
                        cx = x + random.randint(-2, 2)
                        cy = y + random.randint(-2, 2)
                        cv2.circle(img, (cx, cy), bubble_r_px - random.randint(0, 2), (55, 55, 55), -1)
                    continue

            # Regular fill
            y = int(id_y_start + correct_val * row_step_px)
            cx = x + random.randint(-2, 2)
            cy = y + random.randint(-2, 2)
            cv2.circle(img, (cx, cy), bubble_r_px - random.randint(0, 2), (55, 55, 55), -1)

        # --- Draw Version bubble ---
        version_y = int(h * 0.35)
        version_x_start = int(w * 0.08)

        # Map version letter to index
        correct_ver_idx = -1
        if version in VERSION_LETTERS:
            correct_ver_idx = VERSION_LETTERS.index(version)

        if make_ver_issue:
            ver_issue_type = random.choice(["missing", "multi"])
            if ver_issue_type == "missing":
                # Do nothing
                pass
            elif ver_issue_type == "multi" and correct_ver_idx != -1:
                # Fill correct bubble + another
                other_ver_idx = (correct_ver_idx + 1) % active_versions
                for v in [correct_ver_idx, other_ver_idx]:
                    x = int(version_x_start + v * bubble_step_px)
                    cx = x + random.randint(-2, 2)
                    cy = version_y + random.randint(-2, 2)
                    cv2.circle(img, (cx, cy), bubble_r_px - random.randint(0, 2), (55, 55, 55), -1)
        elif correct_ver_idx != -1:
            x = int(version_x_start + correct_ver_idx * bubble_step_px)
            cx = x + random.randint(-2, 2)
            cy = version_y + random.randint(-2, 2)
            cv2.circle(img, (cx, cy), bubble_r_px - random.randint(0, 2), (55, 55, 55), -1)

        # --- Draw Question bubbles ---
        rows_per_col = math.ceil(active_questions / 3)
        q_y_start = int(h * 0.40)
        q_x_starts = [int(w * 0.08), int(w * 0.38), int(w * 0.68)]

        for q_idx, (q_num, cell_idx) in enumerate(q_cols):
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

            # Randomly create missing/multi answer issue on 5% of questions
            if random.random() < 0.05:
                q_issue_type = random.choice(["missing", "multi"])
                if q_issue_type == "missing":
                    # Skip completely
                    continue
                elif q_issue_type == "multi" and correct_opt_idx != -1:
                    # Fill two different bubbles
                    other_opt_idx = (correct_opt_idx + 1) % active_options
                    for o in [correct_opt_idx, other_opt_idx]:
                        x = int(base_x + (o + 1) * bubble_step_px)
                        cx = x + random.randint(-2, 2)
                        cy = y + random.randint(-2, 2)
                        cv2.circle(img, (cx, cy), bubble_r_px - random.randint(0, 2), (55, 55, 55), -1)
                    continue

            if correct_opt_idx != -1:
                x = int(base_x + (correct_opt_idx + 1) * bubble_step_px)
                cx = x + random.randint(-2, 2)
                cy = y + random.randint(-2, 2)
                cv2.circle(img, (cx, cy), bubble_r_px - random.randint(0, 2), (55, 55, 55), -1)

        # 5. Make the PDF look realistic: a little tilted or skewed
        angle = random.uniform(-1.2, 1.2)  # subtle tilt between -1.2 to +1.2 degrees
        M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
        img = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))

        # Convert to compressed JPEG to keep the file size extremely small
        _, img_encoded = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
        pil_pages.append(img_encoded.tobytes())


    # Save all pages as a multipage PDF using PyMuPDF
    if pil_pages:
        out_doc = fitz.open()
        for img_bytes in pil_pages:
            page = out_doc.new_page(width=w, height=h)
            rect = fitz.Rect(0, 0, w, h)
            page.insert_image(rect, stream=img_bytes)
        out_doc.save(output_pdf)
        out_doc.close()
        print(f"Successfully generated {len(pil_pages)} realistic scan pages in: {output_pdf}")


if __name__ == "__main__":
    main()
