import re
import typer
from pathlib import Path
from typing import Optional, List
import sys
import os
import shutil
import platform

from .. import helpers
from ..config import log, VENV_DIR_NAME, REQ_FILE_NAME, LOCK_FILE_NAME, CONFIG_FILE_NAME, EXCLUDE_DIRS

app = typer.Typer(help="Core project setup and execution commands.")

# --- Venv Management ---

def _ensure_venv(project_dir: Path, create_if_missing: bool = True) -> Optional[Path]:
    """Internal helper to find or create and return the venv path."""
    venv_path = helpers.find_venv(project_dir)
    if venv_path:
        log.info(f"Found existing virtualenv: {venv_path}")
        return venv_path

    if not create_if_missing:
        log.error(f"No virtual environment ({VENV_DIR_NAME}) found in {project_dir}.")
        log.info("Run 'pippy init' to create one.")
        raise typer.Exit(1)

    # Create venv
    target_venv_path = project_dir / VENV_DIR_NAME
    log.info(f"Creating new virtual environment in {target_venv_path}...")
    try:
        # Use sys.executable to ensure venv uses the same Python version pippy runs with
        # unless a different one is explicitly managed (e.g., via pyenv)
        rc, _, err = helpers.run_cmd([sys.executable, "-m", "venv", str(target_venv_path)], cwd=project_dir, check=False)
        if rc != 0:
            log.error(f"Failed to create virtual environment.")
            if err:
                typer.echo(helpers.style(f"Error Output:\n{err}", fg=helpers.colors.RED), err=True)
            raise typer.Exit(1)
        log.info("Virtual environment created successfully.")
        return target_venv_path
    except Exception as e:
        log.error(f"An error occurred during venv creation: {e}")
        raise typer.Exit(1)



@app.command("init")
def init_project(
    dir: Optional[Path] = typer.Argument(None, help="Project directory (default: current directory).", exists=False, file_okay=False, dir_okay=True, resolve_path=True)
):
    """Creates and initializes a Python virtual environment (.venv)."""
    project_dir = helpers.get_project_dir(dir)
    log.info(f"Initializing project in: {project_dir}")

    venv_path = _ensure_venv(project_dir, create_if_missing=True)
    helpers.ensure_tool_installed("pipreqs", "pipreqs", venv_path, project_dir)
    # Check if pipreqs is installed in the venv
    if not venv_path: return # Error handled in _ensure_venv

    # Optionally, install base packages or perform other setup here
    # helpers.run_pip_cmd(["install", "--upgrade", "pip", "setuptools", "wheel"], venv_path, project_dir)

    log.info(f"Virtual environment ready at: {venv_path}")
    if platform.system() == "Windows":
        activate_cmd = f"{venv_path}\\Scripts\\activate"
    else:
        activate_cmd = f"source {venv_path}/bin/activate"
    log.info(f"To activate it manually, run: {activate_cmd}")


# pippy/commands/core.py

# ... (other imports) ...
from .. import helpers
from ..config import log, VENV_DIR_NAME, REQ_FILE_NAME, CONFIG_FILE_NAME, EXCLUDE_DIRS # Import EXCLUDE_DIRS


# ... (other commands like init) ...

@app.command("install")
def install_deps(
    dir: Optional[Path] = typer.Argument(None, help="Project directory (default: current directory).", exists=True, file_okay=False, dir_okay=True, resolve_path=True),
    force_req_gen: bool = typer.Option(False, "--force-req", "-f", help=f"Force regeneration of {REQ_FILE_NAME} using pipreqs."),
    skip_main_config: bool = typer.Option(False, "--skip-main", help="Skip configuring the main script."),
):
    """
    Installs dependencies. Optionally generates requirements.txt (using pipreqs)
    and configures the main runnable script.
    """
    project_dir = helpers.get_project_dir(dir)
    log.info(f"Setting up project in: {project_dir}")
    venv_path = _ensure_venv(project_dir, create_if_missing=True)
    if not venv_path: return

    # Verify VENV_DIR_NAME is in EXCLUDE_DIRS (from config.py)
    # This is just a sanity check during development; EXCLUDE_DIRS should be correct
    if VENV_DIR_NAME not in EXCLUDE_DIRS:
        log.warning(f"Configuration issue: '{VENV_DIR_NAME}' not found in EXCLUDE_DIRS set in config.py. Pipreqs might scan the virtual environment.")
        # Consider adding it dynamically if needed, though fixing config.py is better:
        # EXCLUDE_DIRS.add(VENV_DIR_NAME)

    req_file = project_dir / REQ_FILE_NAME

    # --- Section 1: Generate requirements.txt if needed or forced ---
    if force_req_gen or not req_file.exists():
        log.info(f"Ensuring 'pipreqs' is installed in the virtual environment '{venv_path.name}'...")
        try:
            helpers.ensure_tool_installed("pipreqs", "pipreqs", venv_path, project_dir)
        except typer.Exit:
             log.error("Cannot proceed with generating requirements without 'pipreqs'.")
             raise

        log.info(f"Generating {REQ_FILE_NAME} using 'pipreqs'...")
        python_exe = helpers.get_venv_python(venv_path)
        if not python_exe:
             log.error(f"Critical error: Could not find python executable in the verified venv: {venv_path}")
             raise typer.Exit(1)

        pipreqs_base_cmd = [
            "pipreqs",
            ".",
            "--ignore",
            ','.join(EXCLUDE_DIRS)
        ]

        # --- Add Debug Logging for the Full Command ---
        # Use shlex.join for better quoting representation if needed, but simple join is ok for debug
        log.info(f"Running pipreqs command: {' '.join(pipreqs_base_cmd)}")
        # ---------------------------------------------

        rc, out, err = helpers.run_cmd(pipreqs_base_cmd, cwd=project_dir, capture=True, check=False)

        if rc != 0:
            log.error(f"'python -m pipreqs' failed (exit code {rc}).")
            if err:
                typer.echo(helpers.style(f"pipreqs Error Output:\n{err}", fg=helpers.colors.RED), err=True)
            if force_req_gen or not req_file.exists():
                 log.error(f"Failed to generate required {REQ_FILE_NAME}. Halting installation.")
                 raise typer.Exit(1)
            else:
                 log.error(f"pipreqs failed. Cannot guarantee dependencies are up-to-date. Halting installation.")
                 raise typer.Exit(1)
        else:
             try:
                 count = len(req_file.read_text().splitlines())
                 log.info(f"{REQ_FILE_NAME} generated/updated successfully with {count} packages.")
             except FileNotFoundError:
                 log.error(f"{REQ_FILE_NAME} not found after pipreqs reported success. Check pipreqs output.")
                 raise typer.Exit(1)
             except Exception as e:
                 log.warning(f"Could not count packages in generated {req_file}: {e}")


    # --- Section 2: Install dependencies from requirements.txt ---
    if req_file.exists():
        log.info(f"Installing dependencies from {req_file}...")
        try:
            # Use run_pip_cmd to ensure installation into the venv
            helpers.run_pip_cmd(["install", "--upgrade", "-r", str(req_file)], venv_path, project_dir, check=True)
            log.info("Dependencies installed successfully.")
        except typer.Exit:
            log.error(f"Failed to install dependencies from {req_file}.")
            # Optionally trigger 'pippy ask' here or provide more specific guidance
            raise # Re-raise the Exit exception from run_pip_cmd
    else:
        # This case should only be reached if generation wasn't forced and the file didn't exist initially
        log.warning(f"{req_file} not found and generation was not requested/forced.")
        log.info("No dependencies installed.")
        log.info("You can generate it using 'pippy install --force-req' or create it manually.")


    # --- Section 3: Configure main script (if not skipped) ---
    if not skip_main_config:
        try:
            # Assuming configure_main exists and works correctly
            configure_main(project_dir)
        except Exception as e:
            log.warning(f"Could not configure main script: {e}")


def configure_main(project_dir: Path):
    """Prompts user to select a main Python script if not already configured."""
    config = helpers.read_config(project_dir)
    if config.get("main"):
        log.info(f"Main script already configured: {config['main']}")
        return

    log.info("Searching for potential main scripts...")
    py_files = helpers.find_python_files(project_dir)
    main_candidates = [f for f in py_files if helpers.check_for_main_block(f)]

    selected_main: Optional[Path] = None

    if not main_candidates:
        log.warning("No files with 'if __name__ == \"__main__\":' found.")
        # Optionally prompt user to enter path manually
        manual_path_str = typer.prompt("Enter path to main Python script (relative to project root), or leave blank to skip", default="", show_default=False)
        if manual_path_str:
            manual_path = (project_dir / manual_path_str).resolve()
            if manual_path.is_file() and manual_path.suffix == '.py':
                 selected_main = manual_path
            else:
                 log.error(f"Invalid path or not a Python file: {manual_path_str}")
                 return # Skip configuration
        else:
            log.info("Skipping main script configuration.")
            return

    elif len(main_candidates) == 1:
        selected_main = main_candidates[0]
        log.info(f"Found single potential main script: {selected_main.relative_to(project_dir)}")
        if not helpers.prompt_yes_no(f"Use '{selected_main.relative_to(project_dir)}' as the main script?", default_yes=True):
            selected_main = None # User declined

    else: # Multiple candidates
        typer.echo("Multiple potential main scripts found:")
        for i, f in enumerate(main_candidates):
            typer.echo(f"  {i+1}) {f.relative_to(project_dir)}")

        while selected_main is None:
            try:
                choice = typer.prompt("Select the number of the main script (or 0 to skip)", type=int, default=0)
                if choice == 0:
                    log.info("Skipping main script configuration.")
                    return
                if 1 <= choice <= len(main_candidates):
                    selected_main = main_candidates[choice - 1]
                else:
                    typer.echo(helpers.style("Invalid selection.", fg=helpers.colors.YELLOW))
            except ValueError:
                 typer.echo(helpers.style("Invalid input. Please enter a number.", fg=helpers.colors.YELLOW))

    if selected_main:
        relative_path = selected_main.relative_to(project_dir)
        helpers.update_config_value(project_dir, "main", str(relative_path))
        log.info(f"Main script set to '{relative_path}' in {CONFIG_FILE_NAME}")


@app.command("run")
def run_script(
    target: Path = typer.Argument(..., help="Python file to run, or a directory containing pippy.json.", exists=True, resolve_path=True),
    args: Optional[List[str]] = typer.Argument(None, help="Arguments to pass to the script."),
):
    """Runs a Python script or the configured main script in a project directory."""
    target = target.resolve()
    run_args = args if args else []

    if target.is_file() and target.suffix == '.py':
        project_dir = target.parent
        script_to_run = target
        log.info(f"Running specific file: {script_to_run}")
    elif target.is_dir():
        project_dir = target
        config = helpers.read_config(project_dir)
        main_script_rel = config.get("main")
        if not main_script_rel:
            log.error(f"No 'main' script configured in {project_dir / CONFIG_FILE_NAME}.")
            log.info("Run 'pippy install' or configure it manually.")
            raise typer.Exit(1)
        script_to_run = (project_dir / main_script_rel).resolve()
        if not script_to_run.exists():
             log.error(f"Configured main script not found: {script_to_run}")
             raise typer.Exit(1)
        log.info(f"Running configured main script: {script_to_run.relative_to(project_dir)}")
    else:
        log.error(f"Target '{target}' is not a valid Python file or project directory.")
        raise typer.Exit(1)

    venv_path = helpers.find_venv(project_dir)
    if not venv_path and helpers.ACTIVE_VIRTUAL_ENV:
        # If pippy is running in a venv, but target project has none, use pippy's venv? Risky.
        # Best practice: the target project should have its own venv.
        log.warning(f"Running script {script_to_run.name} without a dedicated project virtualenv ({VENV_DIR_NAME}). Using environment where pippy is running.")
        # Or require venv?
        # log.error(f"Project directory {project_dir} does not have a .venv. Run 'pippy init'.")
        # raise typer.Exit(1)
    elif not venv_path:
        log.warning(f"No virtual environment found in {project_dir}. Running with system Python.")
        # Or require venv?

    try:
        # Use run_python_cmd to ensure correct interpreter is used
        rc, _, _ = helpers.run_python_cmd([str(script_to_run)] + run_args, venv_path, cwd=project_dir, check=False)
        if rc != 0:
             log.warning(f"Script exited with non-zero status: {rc}")
             # Don't Exit pippy itself unless the script execution fundamentally failed
             # sys.exit(rc) # Forward the script's exit code
    except typer.Exit as e:
        # Catch Exit from run_python_cmd if python itself couldn't be found etc.
        log.error("Failed to execute the script.")
        raise e
    except Exception as e:
        log.error(f"An error occurred while trying to run the script: {e}")
        raise typer.Exit(1)


@app.command("start")
def start_project(
    args: Optional[List[str]] = typer.Argument(None, help="Arguments to pass to the main script."),
):
    """Shortcut for 'pippy run .'"""
    log.debug("Running start command (equivalent to 'run .')")
    run_script(target=Path("."), args=args)


@app.command("lock")
def lock_deps(
    dir: Optional[Path] = typer.Argument(None, help="Project directory (default: current directory).", exists=True, file_okay=False, dir_okay=True, resolve_path=True),
    output_file: Optional[Path] = typer.Option(None, "--output", "-o", help=f"Output file name (default: {LOCK_FILE_NAME}).", resolve_path=False), # Resolve relative to project_dir later
):
    """Freezes current environment dependencies into a lock file."""
    project_dir = helpers.get_project_dir(dir)
    venv_path = _ensure_venv(project_dir, create_if_missing=False) # Require venv
    if not venv_path: return

    lock_file_name = output_file if output_file else LOCK_FILE_NAME
    output_path = project_dir / lock_file_name

    log.info(f"Freezing dependencies to {output_path}...")
    try:
        rc, output, err = helpers.run_pip_cmd(["freeze"], venv_path, project_dir, capture=True, check=False)
        if rc != 0:
            log.error("pip freeze failed.")
            if err: typer.echo(helpers.style(f"Error Output:\n{err}", fg=helpers.colors.RED), err=True)
            raise typer.Exit(1)

        with open(output_path, 'w') as f:
            f.write(output)

        count = len(output.splitlines())
        log.info(f"Wrote {count} package pins to {output_path}")

    except Exception as e:
        log.error(f"Failed to write lock file: {e}")
        raise typer.Exit(1)


@app.command("clean")
def clean_pycache(
    dir: Optional[Path] = typer.Argument(None, help="Project directory (default: current directory).", exists=True, file_okay=False, dir_okay=True, resolve_path=True)
):
    """Removes __pycache__ directories and *.pyc/pyo files."""
    project_dir = helpers.get_project_dir(dir)
    log.info(f"Cleaning Python cache files in {project_dir}...")
    count_dirs = 0
    count_files = 0

    for item in project_dir.rglob("*"):
        # Check if the item is within an excluded directory (like .venv)
        is_excluded = False
        try:
            relative_path = item.relative_to(project_dir)
            if relative_path.parts and relative_path.parts[0] in EXCLUDE_DIRS:
                is_excluded = True
        except (ValueError, IndexError):
            pass # Should not happen with rglob from project_dir but handle robustly

        if is_excluded:
            continue

        # Remove __pycache__ directories
        if item.is_dir() and item.name == "__pycache__":
            log.debug(f"Removing directory: {item}")
            try:
                shutil.rmtree(item)
                count_dirs += 1
            except Exception as e:
                log.warning(f"Could not remove directory {item}: {e}")

        # Remove .pyc/.pyo files
        elif item.is_file() and item.suffix in [".pyc", ".pyo"]:
            log.debug(f"Removing file: {item}")
            try:
                item.unlink()
                count_files += 1
            except Exception as e:
                log.warning(f"Could not remove file {item}: {e}")

    log.info(f"Cleaning complete. Removed {count_dirs} directories and {count_files} files.")


@app.command("shell")
def project_shell(
    dir: Optional[Path] = typer.Argument(None, help="Project directory (default: current directory).", exists=True, file_okay=False, dir_okay=True, resolve_path=True)
):
    """Starts a new interactive shell with the virtual environment activated."""
    project_dir = helpers.get_project_dir(dir)
    venv_path = _ensure_venv(project_dir, create_if_missing=False) # Require venv
    if not venv_path: return

    shell_executable = os.environ.get("SHELL", shutil.which("bash") or shutil.which("sh")) # Default to bash/sh
    if not shell_executable:
        log.error("Could not determine shell executable (SHELL environment variable not set?).")
        raise typer.Exit(1)

    log.info(f"Spawning interactive shell ({os.path.basename(shell_executable)}) with venv activated...")
    log.info(f"Venv: {venv_path}")
    log.info("Type 'exit' or press Ctrl+D to return.")

    activate_script = None
    if platform.system() == "Windows":
        # Activation in Windows cmd/powershell is more complex to script reliably.
        # For cmd.exe, it might be 'call <venv>\Scripts\activate.bat'
        # For PowerShell, it might be '<venv>\Scripts\Activate.ps1' (check execution policy)
        # The most reliable way might be to just inform the user.
        log.warning("Automatic shell activation on Windows is complex.")
        log.info(f"Please activate manually in the new shell:")
        log.info(f"  cmd.exe:    call {venv_path}\\Scripts\\activate.bat")
        log.info(f"  PowerShell: {venv_path}\\Scripts\\Activate.ps1")
        # Just launch the default shell without trying to activate
        subprocess.run([os.environ.get('COMSPEC', 'cmd.exe')], cwd=project_dir)

    else: # POSIX-like shells (bash, zsh, etc.)
        activate_script = venv_path / "bin" / "activate"
        if not activate_script.exists():
            log.error(f"Activation script not found: {activate_script}")
            raise typer.Exit(1)

        # Construct a command to source the activate script and then run an interactive shell
        # Using 'exec' replaces the intermediate shell process
        # Note: This relies on the shell supporting 'source' and the '-i' flag
        # It might not work perfectly for all shell types or configurations.
        cmd = f'source "{activate_script}" && exec "{shell_executable}" -i'
        try:
            # We need shell=True here to interpret the 'source' and '&&' commands
            subprocess.run([shell_executable, "-c", cmd], cwd=project_dir, check=True, shell=False) # Use -c flag instead of full shell=True if possible
        except FileNotFoundError:
             log.error(f"Shell executable not found: {shell_executable}")
             raise typer.Exit(1)
        except Exception as e:
            log.error(f"Failed to spawn activated shell: {e}")
            log.info("Attempting to launch basic shell. Please activate manually:")
            log.info(f"  source {activate_script}")
            try:
                subprocess.run([shell_executable, "-i"], cwd=project_dir)
            except Exception as e2:
                 log.error(f"Failed to launch basic shell either: {e2}")
                 raise typer.Exit(1)

    log.info("Exited project shell.")


@app.command("info")
def project_info(
     dir: Optional[Path] = typer.Argument(None, help="Project directory (default: current directory).", exists=True, file_okay=False, dir_okay=True, resolve_path=True)
):
    """Shows detected requirements (via pipreqs) and project file tree."""
    project_dir = helpers.get_project_dir(dir)
    venv_path = _ensure_venv(project_dir, create_if_missing=False) # Require venv for pipreqs
    if not venv_path: return

    typer.echo("\n" + helpers.style("=== Requirements (Detected by pipreqs) ===", bold=True))
    try:
        helpers.ensure_tool_installed("pipreqs", "pipreqs", venv_path, project_dir, check_command=["pipreqs"])
        pipreqs_cmd = helpers.get_executable(venv_path, "pipreqs")
        cmd = [pipreqs_cmd, str(project_dir), "--print"] # Removed --force, just print detected
        for ignore_dir in EXCLUDE_DIRS:
             cmd.extend(["--ignore", ignore_dir])

        if " -m " in pipreqs_cmd:
             python_exe, *module_args = pipreqs_cmd.split(" ", 2)
             cmd = [python_exe.strip('"')] + module_args + cmd[1:]

        rc, out, err = helpers.run_cmd(cmd, cwd=project_dir, capture=True, check=False)
        if rc != 0:
             log.error("pipreqs --print failed.")
             if err: typer.echo(helpers.style(f"Error Output:\n{err}", fg=helpers.colors.RED), err=True)
             typer.echo("Could not retrieve requirements.")
        else:
             if out:
                 typer.echo(out)
             else:
                 typer.echo("(No requirements detected by pipreqs)")
    except Exception as e:
        log.error(f"Failed to run pipreqs: {e}")
        typer.echo("Could not retrieve requirements.")


    typer.echo("\n" + helpers.style("=== Python File Tree ===", bold=True))
    py_files = helpers.find_python_files(project_dir)

    if not py_files:
        typer.echo("(No Python files found outside excluded directories)")
        return

    # Basic tree structure simulation
    tree = {}
    for fpath in sorted(py_files):
        rel_path = fpath.relative_to(project_dir)
        parts = rel_path.parts
        node = tree
        for i, part in enumerate(parts):
            if i == len(parts) - 1: # It's the file
                 node[part] = None # Mark as file
            else: # It's a directory
                if part not in node:
                    node[part] = {}
                node = node[part]

    def print_tree(node, indent=""):
        items = sorted(node.items())
        for i, (name, children) in enumerate(items):
            connector = "└── " if i == len(items) - 1 else "├── "
            typer.echo(f"{indent}{connector}{name}")
            if children is not None: # It's a directory
                new_indent = indent + ("    " if i == len(items) - 1 else "│   ")
                print_tree(children, new_indent)

    print_tree(tree)
    typer.echo("")

# Add other core commands (update) following similar patterns...
# Remember to create files for other command groups (qa.py, dev.py, etc.) and import/add them in main.py