"""All magic numbers, file extensions, limits, and version string."""

from euler_omr import __version__

APP_NAME = "Euler OMR"
APP_VERSION = __version__
ORG_NAME = "EulerOMR"
ORG_DOMAIN = "github.com/MustafaMahmoud-ILE/EulerOMR"

# File extensions
EOMRT_EXTENSION = ".eomrt"
EOMRT_FILTER = "Euler OMR Template (*.eomrt)"
EOMRP_EXTENSION = ".eomrp"
EOMRP_FILTER = "Euler OMR Project (*.eomrp)"
PDF_FILTER = "PDF Files (*.pdf)"
IMAGE_FILTER = "Images (*.png *.jpg *.jpeg *.svg)"

# File format version
FILE_FORMAT_VERSION = "1.0"

# Window sizes
MIN_WINDOW_WIDTH = 960
MIN_WINDOW_HEIGHT = 540
DEFAULT_WINDOW_WIDTH = 1280
DEFAULT_WINDOW_HEIGHT = 720

# Template limits
ID_DIGITS_MIN = 5
ID_DIGITS_MAX = 14
ID_DIGITS_DEFAULT = 10

NUM_VERSIONS_MIN = 2
NUM_VERSIONS_MAX = 26
NUM_VERSIONS_DEFAULT = 4

NUM_QUESTIONS_MIN = 60
NUM_QUESTIONS_MAX = 99
NUM_QUESTIONS_DEFAULT = 60

NUM_OPTIONS_MIN = 4
NUM_OPTIONS_MAX = 8
NUM_OPTIONS_DEFAULT = 4

# Project limits
ACTIVE_QUESTIONS_MIN = 5
ACTIVE_OPTIONS_MIN = 2
ACTIVE_VERSIONS_MIN = 2

# OMR geometry
BUBBLE_RADIUS_CM = 0.22
BUBBLE_STEP_CM = 0.6
ROW_STEP_CM = 0.5
FILL_THRESHOLD = 128  # 0-255 scale

# Scan DPI
SCAN_DPI = 200

# Auto-contrast issue threshold
AUTO_CONTRAST_ISSUE_THRESHOLD = 5

# Recents
MAX_RECENT_FILES = 10

# Logging
LOG_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
LOG_BACKUP_COUNT = 3

# Analysis thresholds
EASY_THRESHOLD = 0.75
MODERATE_THRESHOLD = 0.40
CONFUSION_THRESHOLD = 0.35
FAIRNESS_THRESHOLD = 0.10  # 10% of max_score


# Version letters
VERSION_LETTERS = [chr(ord('A') + i) for i in range(26)]

# Option letters
OPTION_LETTERS = [chr(ord('A') + i) for i in range(8)]
