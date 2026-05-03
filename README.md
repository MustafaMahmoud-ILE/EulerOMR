# Euler OMR

A production-grade desktop application for designing OMR (Optical Mark Recognition) templates, scanning and marking student answer sheets, and running statistical analysis on grading results.

![Euler OMR](icon.png)

## Screenshots

### Welcome Screen
![Welcome](assets/screenshots/welcome.png)

### Template Designer
![Template Designer](assets/screenshots/template.png)

### Project Manager
![Project](assets/screenshots/project.png)

### Review Issues
![Review Issues](assets/screenshots/review_issues.png)

### Manage Answer Keys
![Answer Keys](assets/screenshots/manage_answer_keys.png)

## Features

- **Template Designer** — Design OMR answer sheets with configurable ID digits, versions, questions, and options. Compile to PDF via LaTeX.
- **Scan Reader** — Import scanned PDFs, automatically detect corner marks, read student IDs, versions, and answers via bubble fill analysis.
- **Issue Review** — Color-coded scan results table with per-field review dialog for resolving ambiguous reads.
- **Answer Key Management** — Tabbed dialog for entering correct answers per version with multi-select support.
- **Automated Grading** — Apply answer keys to scan results and export grades to XLSX.
- **Statistical Analysis** — Mean, median, mode, standard deviation per version. Per-question difficulty classification. Version fairness comparison.
- **Analysis Report** — Auto-generated PDF report with charts (histograms, boxplots, bar charts).

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

## Requirements

- Python 3.11+
- PySide6 6.7+
- pdflatex (TinyTeX recommended for compilation)

## Project Structure

```
euler_omr/          # Main package
  core/             # Template compiler, scan reader, grader, analysis, report builder, XLSX exporter
  models/           # Data models (TemplateConfig, ProjectConfig, ScanResult, AnswerKey)
  file_io/          # .eomrt and .eomrp file handlers
  workers/          # QRunnable workers for background tasks
  ui/               # UI layer
    widgets/        # Log panel, progress overlay, image preview, bubble crop view
    tabs/           # Welcome, Template, Project tabs
    dialogs/        # Answer key, review page, TinyTeX install, unsaved changes
assets/             # Logo, fonts, icons
tests/              # Unit tests
```

## File Formats

- **`.eomrt`** — Euler OMR Template: base64-packed JSON bundle containing template config, compiled PDF, and logo.
- **`.eomrp`** — Euler OMR Project: base64-packed JSON bundle containing project config, embedded template, scans, scan results, and answer keys.

## License

MIT
