import os
from pathlib import Path
import logging

# --- Constants ---
APP_NAME = "pippy"
VERSION = "1.0.2" # Keep in sync with pyproject.toml
CONFIG_FILE_NAME = "pippy.json"
LOCK_FILE_NAME = "requirements.lock"
REQ_FILE_NAME = "requirements.txt"
VENV_DIR_NAME = ".venv"
LOG_FILE_NAME = f"{APP_NAME}.log"

# --- Basic Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    handlers=[
        # logging.FileHandler(LOG_FILE_NAME), # Optionally log to file
        logging.StreamHandler() # Log to stderr/stdout
    ]
)
log = logging.getLogger(APP_NAME)

# --- Environment ---
# Respect existing VIRTUAL_ENV if pippy is run from within one
ACTIVE_VIRTUAL_ENV = os.environ.get("VIRTUAL_ENV")

# --- Project Root Detection (heuristic) ---
# Assume the project root is the directory where pippy is invoked,
# unless overridden by a command argument.
DEFAULT_PROJECT_DIR = Path.cwd()

# --- OpenAI Config ---
OPENAI_API_KEY_ENV_VAR = "OPENAI_API_KEY"

# --- Excluded Dirs for Searches/Scans ---
EXCLUDE_DIRS = {VENV_DIR_NAME, "venv", "__pycache__", ".git", ".hg", "dist", "build", "docs/_build"}
EXCLUDE_PATHS_GLOB = [f"**/{d}/**" for d in EXCLUDE_DIRS]