# pippy

🚧 *A work-in-progress Python project helper. Use at your own risk (for now!).* 🚧

---

## What is this? (And why you might look elsewhere... for now)

Pippy aims to bring simple, helpful project management workflows to Python, inspired by tools common in other ecosystems (like npm, mvn, gradle). As someone involved in developer experience (Spring team, open-source projects), I wanted a tool for my own Python work that reduces friction, especially around environment setup (looking at you, ML on different hardware!) and deciphering opaque Python errors.

This is **very much a work in progress** and built primarily for my own needs. It has rough edges! However, the core ideas are:

*   **Virtual Env First:** Commands generally expect and work within a local `.venv` directory, created easily with `pippy init`.
*   **Simplified Dependencies:** `pippy install` can use `pipreqs` (if installed) to auto-generate a `requirements.txt` and install dependencies, getting you started quickly.
*   **Integrated AI Help:** Tired of searching for cryptic Python errors? `pippy ask "Why does this import fail?"` sends project context (code files, recent errors if wrapped) to OpenAI for an explanation right in your terminal.
*   **Common Workflow Commands:** A single `pippy` command provides verbs like `run`, `test`, `lock`, `format`, `lint`, `audit`, and even an `ml` command for TensorFlow sanity checks. This aims to provide a more consistent interface, especially helpful if you're coming to Python from other languages.

Pippy is being developed primarily on **Linux** and **macOS**. While the core Python code *should* work on **Windows**, some commands invoking shell tools might need adjustments. It's **not** a package manager like pip or conda; it's a workflow assistant that *uses* those tools.

### Why I Built This (The AI Helper)

Frankly, I find Python's error messages can be unhelpful sometimes. The built-in AI helper (`pippy ask`) is a key feature born from this frustration. When a command fails (or you just ask directly), it can provide context-aware explanations from GPT, hopefully saving you a trip to the browser and keeping you focused.

### Seriously, Consider Other Tools First

There are mature, robust, and widely-used tools in the Python ecosystem (like Poetry, PDM, Hatch, or just plain pip/venv). You should probably investigate those first!

As I continue using Python, I'll keep improving Pippy based on my experiences. If you stumble upon this and are interested in building developer tools, especially those integrating AI assistance (like providing context, memory, task execution), feel free to reach out.

---

## Quick Start (Python CLI Version)

```bash
# Recommended installation using pipx (isolates the tool)
pipx install git+https://github.com/kbastani/pippy
```

Initialize & install dependencies:

```bash
# Navigate to your project directory
cd my-python-project

# Create and set up the virtual environment (.venv)
pippy init

# Generate requirements.txt (optional, needs pipreqs) and install deps
# Or installs from existing requirements.txt
pippy install

# See detected dependencies and project structure
pippy info
```

Run code & tests:

```bash
# Run the configured main script (from pippy.json) or a specific file
pippy run .
pippy run my_script.py

# Run tests (uses pytest if found, falls back to unittest)
pippy test
```

Get AI help:

```bash
# Ask about a specific problem
pippy ask "How do I install tensorflow with GPU support on Ubuntu?"

# If a pippy command fails (e.g., during install), it might suggest using 'ask'
# (Future enhancement: automatically pipe error context to 'ask')
```

> ✨ **OpenAI API Key:** The first time you use `pippy ask`, it will check for the `OPENAI_API_KEY` environment variable. If not found, it will prompt you to enter one. You'll have the option to store the key or a flag (`use_env_key`) in a local `pippy.json` config file for future use.

---

## Command Summary

| Command             | Description                                                  | Status          |
| :------------------ | :----------------------------------------------------------- | :-------------- |
| `init [dir]`        | Creates/ensures `.venv/` in the target directory (default: cwd) | ✅ Implemented  |
| `install [dir]`     | Installs deps (`requirements.txt`), optionally generates it via `pipreqs`, configures `main` script in `pippy.json` | ✅ Implemented  |
| `update [dir]`      | Regenerates `requirements.txt` (via `pipreqs` if forced/needed) & upgrades packages | ✅ Implemented  |
| `run [file\|dir]`   | Runs a specified `.py` file or the configured `main` script  | ✅ Implemented  |
| `start`             | Alias for `pippy run .`                                      | ✅ Implemented  |
| `info`              | Shows detected requirements (via `pipreqs`) + Python file tree | ✅ Implemented  |
| `lock`              | Freezes dependencies (`pip freeze`) → `requirements.lock`    | ✅ Implemented  |
| `test`              | Runs `pytest` (or `unittest` fallback)                       | ✅ Implemented  |
| `clean`             | Removes `__pycache__` directories & `*.pyc`/`*.pyo` files    | ✅ Implemented  |
| `shell`             | Spawns a new subshell with the project's venv activated (experimental) | ✅ Implemented  |
| `ask [question]`    | Asks GPT about the project using code context                | ✅ Implemented  |
| `develop`           | Installs project in editable mode (`pip install -e .`)       | ✅ Implemented  |
| `pkg`               | Builds sdist + wheel (`python -m build`)                     | ✅ Implemented  |
| `publish`           | Uploads `dist/*` contents via `twine`                        | ✅ Implemented  |
| `lint`              | Runs `flake8` (installs if needed)                           | ✅ Implemented  |
| `format`            | Runs `isort` & `black` (installs if needed)                  | ✅ Implemented  |
| `audit`             | Runs security scan with `pip-audit` (installs if needed)     | ✅ Implemented  |
| `coverage`          | Runs tests with `coverage` and shows report (installs if needed) | ✅ Implemented  |
| `docs init`         | Scaffolds Sphinx docs in `docs/` (installs Sphinx if needed) | ✅ Implemented  |
| `docs build`        | Builds Sphinx HTML docs (`docs/_build/html`)                 | ✅ Implemented  |
| `bump <level>`      | Bumps version (patch/minor/major) in `pyproject.toml`      | 🚧 Planned      |
| `doctor`            | Runs quick environment health checks                         | ✅ Implemented  |
| `ci-setup`          | Generates basic CI config file stub (e.g., GitHub Actions)   | 🚧 Planned      |
| `ml`                | Installs TensorFlow (optional) & checks device availability  | ✅ Implemented  |

---

## Installation Internals (Python Version)

*   When you run `pipx install git+https://github.com/kbastani/pippy`, `pipx` does the following:
    1.  Clones the repository.
    2.  Creates an isolated virtual environment specifically for Pippy.
    3.  Builds and installs the Pippy Python package (defined in `pyproject.toml`) and its dependencies (like `typer`, `openai`) into that isolated environment.
    4.  Creates a symbolic link (or shim) to the `pippy` entry point script (defined in `pyproject.toml`'s `[project.scripts]`) somewhere on your system's PATH.
*   Pippy then runs as a standard Python application within its own managed environment, invoking tools like `python`, `pip`, `pytest` etc. either from your project's `.venv` (if found) or potentially from the system PATH.

---

## Developing Pippy

```bash
# Clone the repository
git clone https://github.com/kbastani/pippy
cd pippy

# Create a virtual environment for development
python -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\activate

# Install pippy in editable mode with development dependencies
# (Assuming dev deps are listed under [project.optional-dependencies] "dev" in pyproject.toml)
pip install -e ".[dev]"

# Run tests (assuming pytest is used)
pytest

# Run linters/formatters (if configured, e.g., via pre-commit)
# pre-commit run --all-files
```

*   Pre‑commit hooks might be configured; run `pre-commit install` after cloning if you want to use them automatically before committing.

---

## Roadmap

*   Full Windows support testing & refinement.
*   Built‑in template generation for `pyproject.toml`.
*   More robust `bump` command implementation.
*   Enhanced CI/CD setup command (`ci-setup`).
*   Potential packaging for Homebrew / Scoop / etc. *after* stabilization.

Contributions are welcome, especially for the roadmap items! Please check `CONTRIBUTING.md` (if it exists and is up-to-date) for any style or testing guidelines. A simple PR with a clear description is often the best way to start.

---

## License

[MIT License](LICENSE)
