# config.py — Configuration and constants

APP_TITLE = "Simple Facts with Simple Images"
APP_SUBTITLE = "Turn long lengthy text into simple fun flashcards"

READING_LEVELS = {
    "Easy (Ages 4-11)": "simple",
    "Medium (Ages 11-18)": "intermediate",
    "Advanced (Ages 18+)": "complex"
}

# Dyslexia-friendly fonts (sans-serif, system fonts only - no external downloads)
FONT_OPTIONS = [
    "Verdana",      # Best for dyslexia, universally available
    "Arial",        # Good for dyslexia, universally available
    "Calibri",      # Good for dyslexia, widely available
    "Tahoma",       # Good for dyslexia, universally available
    "Comic Sans",   # Dyslexia-friendly (controversial but effective)
    "Trebuchet MS", # Clean, legible sans-serif
    "Georgia",      # Serif alternative, good readability
    "Courier New"   # Monospace option for technical content
]

MIN_FONT_SIZE = 12  # Minimum for accessibility
MAX_FONT_SIZE = 40  # Maximum for larger text options
DEFAULT_FONT_SIZE = 16  # 16pt for body text

# Model configs
SUMMARIZATION_MODEL = "facebook/bart-base"
IMAGE_MODEL = "runwayml/stable-diffusion-v1-5"

# Quality settings
MIN_IMAGE_STEPS = 10
MAX_IMAGE_STEPS = 40  
DEFAULT_IMAGE_STEPS = 25
