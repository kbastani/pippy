import subprocess
import sys
import os
import json
import shutil
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
import shlex

from typer import echo, style, colors, Exit

from .config import (
    log, ACTIVE_VIRTUAL_ENV, VENV_DIR_NAME, CONFIG_FILE_NAME,
    REQ_FILE_NAME, EXCLUDE_DIRS, OPENAI_API_KEY_ENV_VAR
)

# --- Environment & Path Helpers ---

def get_project_dir(dir_arg: Optional[Path] = None) -> Path:
    """Determines the target project directory."""
    if dir_arg:
        resolved_dir = dir_arg.resolve()
        if not resolved_dir.is_dir():
            log.error(f"Directory not found: {dir_arg}")
            raise Exit(1)
        return resolved_dir
    return Path.cwd().resolve()

def find_venv(project_dir: Path) -> Optional[Path]:
    """Finds the virtual environment directory (.venv)."""
    venv_path = project_dir / VENV_DIR_NAME
    if venv_path.is_dir() and (venv_path / "pyvenv.cfg").exists():
        return venv_path
    # Could add checks for 'venv' or other names if desired
    return None

def get_venv_python(venv_path: Path) -> Optional[Path]:
    """Gets the path to the python executable within the venv."""
    if sys.platform == "win32":
        python_exe = venv_path / "Scripts" / "python.exe"
    else:
        python_exe = venv_path / "bin" / "python"
    return python_exe if python_exe.exists() else None

def get_executable(venv_path: Optional[Path], command: str) -> str:
    """Gets the command path, preferring the venv's bin/Scripts."""
    if venv_path:
        if sys.platform == "win32":
            exe_path = venv_path / "Scripts" / f"{command}.exe"
            if exe_path.exists():
                return str(exe_path)
            exe_path = venv_path / "Scripts" / command
            if exe_path.exists():
                 return str(exe_path) # For commands without .exe like 'pip' sometimes?
            # Fallback to python -m command inside venv
            python_exe = get_venv_python(venv_path)
            if python_exe:
                 return f'"{python_exe}" -m {command}' # Return string for shell=True or manual parsing
        else:
            exe_path = venv_path / "bin" / command
            if exe_path.exists():
                return str(exe_path)
             # Fallback to python -m command inside venv
            python_exe = get_venv_python(venv_path)
            if python_exe:
                 return f'"{python_exe}" -m {command}'

    # If not in venv or not found in venv, try finding on PATH
    found_path = shutil.which(command)
    if found_path:
        return found_path

    # Last resort: assume it's a module runnable with the current python
    # This might be wrong if pippy itself is in a different venv!
    log.warning(f"Command '{command}' not found in venv or PATH, attempting 'python -m {command}'")
    return f'"{sys.executable}" -m {command}'


# --- Subprocess Execution ---

def run_cmd(
    cmd_list: List[str] | str,
    cwd: Optional[Path] = None,
    capture: bool = False,
    check: bool = True,
    env: Optional[Dict[str, str]] = None,
    shell: bool = False, # Use with caution! Only if cmd is a string.
) -> Tuple[int, str, str]:
    """Runs a command using subprocess, returning status, stdout, stderr."""
    effective_env = os.environ.copy()
    if env:
        effective_env.update(env)

    log.debug(f"Running command: {cmd_list} in {cwd or Path.cwd()}")

    try:
        # If shell=True, cmd_list must be a string
        if shell and not isinstance(cmd_list, str):
             log.error("Cannot use shell=True with a list of arguments.")
             raise Exit(1)
        # If shell=False, quote arguments with spaces if necessary
        if not shell and isinstance(cmd_list, list):
            cmd_list = [shlex.quote(str(arg)) for arg in cmd_list]

        process = subprocess.run(
            cmd_list,
            cwd=cwd,
            capture_output=capture,
            text=True,
            check=False, # We handle the check manually
            env=effective_env,
            shell=shell, # SECURITY RISK if cmd_list comes from untrusted input
        )
        stdout = process.stdout.strip() if process.stdout else ""
        stderr = process.stderr.strip() if process.stderr else ""

        if capture and stdout:
             log.debug(f"Stdout: {stdout}")
        if stderr:
             log.debug(f"Stderr: {stderr}") # Log stderr even if not capturing stdout specifically

        if check and process.returncode != 0:
            log.error(f"Command failed with exit code {process.returncode}: {cmd_list}")
            if stderr:
                echo(style(f"Error Output:\n{stderr}", fg=colors.RED), err=True)
            # Consider raising an exception instead of Exit for better control flow
            raise Exit(process.returncode)

        return process.returncode, stdout, stderr

    except FileNotFoundError:
        log.error(f"Command not found: {cmd_list[0] if isinstance(cmd_list, list) else cmd_list.split()[0]}")
        raise Exit(127)
    except Exception as e:
        log.error(f"An error occurred while running command: {cmd_list}\n{e}")
        raise Exit(1)


def run_python_cmd(
    args: List[str],
    venv_path: Optional[Path],
    cwd: Optional[Path] = None,
    capture: bool = False,
    check: bool = True,
    env: Optional[Dict[str, str]] = None,
) -> Tuple[int, str, str]:
    """Runs a python command, preferring the venv's python."""
    python_exe = sys.executable # Default to current python
    if venv_path:
        venv_python = get_venv_python(venv_path)
        if venv_python:
            python_exe = str(venv_python)
        else:
            log.warning(f"Could not find python executable in venv: {venv_path}")

    cmd = [python_exe] + args
    return run_cmd(cmd, cwd=cwd, capture=capture, check=check, env=env)

def run_pip_cmd(
    args: List[str],
    venv_path: Optional[Path],
    cwd: Optional[Path] = None,
    capture: bool = False,
    check: bool = True,
    env: Optional[Dict[str, str]] = None,
) -> Tuple[int, str, str]:
    """Runs a pip command using the venv's python -m pip."""
    return run_python_cmd(["-m", "pip"] + args, venv_path, cwd, capture, check, env)


# --- Tool Installation/Check Helpers ---

def ensure_tool_installed(
    tool_name: str,
    pip_package: str,
    venv_path: Optional[Path],
    project_dir: Path,
    check_command: Optional[List[str]] = None,
    check_import: Optional[str] = None
):
    """Checks if a tool is installed (via command or import) and installs it if not."""
    installed = False
    python_exe = get_venv_python(venv_path) if venv_path else sys.executable

    # 1. Check if tool command exists or module can be imported
    if check_command:
        cmd_path = get_executable(venv_path, check_command[0])
        # Check if get_executable returned a direct path or a 'python -m' string
        if Path(cmd_path).is_file(): # Direct path
             installed = True
        elif cmd_path.startswith(f'"{python_exe}" -m'): # python -m based
             # Check if the underlying module exists
            try:
                 rc, _, _ = run_python_cmd(["-c", f"import importlib.util; import sys; sys.exit(0 if importlib.util.find_spec('{check_command[0]}') else 1)"], venv_path, project_dir, check=False)
                 installed = (rc == 0)
            except Exception:
                 installed = False # Error running check
        else: # Tool might be on global PATH but not in venv
            installed = bool(shutil.which(cmd_path))
    elif check_import:
        try:
            rc, _, _ = run_python_cmd(["-c", f"import importlib.util; import sys; sys.exit(0 if importlib.util.find_spec('{check_import}') else 1)"], venv_path, project_dir, check=False)
            installed = (rc == 0)
        except Exception as e:
            log.debug(f"Import check failed for {check_import}: {e}")
            installed = False # Error running check

    # 2. Install if not found
    if not installed:
        log.info(f"Tool '{tool_name}' not found or inaccessible, installing '{pip_package}'...")
        try:
            run_pip_cmd(["install", pip_package], venv_path, project_dir, check=True)
            log.info(f"Successfully installed {tool_name}.")
        except Exit as e:
            log.error(f"Failed to install {tool_name} ({pip_package}). Please install it manually.")
            raise e # Re-raise Exit

# --- Configuration File Helpers ---

def read_config(project_dir: Path) -> Dict[str, Any]:
    """Reads the pippy.json configuration file."""
    config_path = project_dir / CONFIG_FILE_NAME
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            log.warning(f"Could not parse {CONFIG_FILE_NAME}. Treating as empty.")
            return {}
        except Exception as e:
            log.warning(f"Error reading {CONFIG_FILE_NAME}: {e}. Treating as empty.")
            return {}
    return {}

def write_config(project_dir: Path, config_data: Dict[str, Any]):
    """Writes data to the pippy.json configuration file."""
    config_path = project_dir / CONFIG_FILE_NAME
    try:
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=2)
        log.debug(f"Configuration saved to {config_path}")
    except Exception as e:
        log.error(f"Failed to write configuration to {config_path}: {e}")
        # Decide if this is a fatal error or not
        # raise Exit(1)

def update_config_value(project_dir: Path, key: str, value: Any):
    """Updates a specific key in the configuration file."""
    config = read_config(project_dir)
    config[key] = value
    write_config(project_dir, config)


# --- Other Helpers ---

def find_python_files(project_dir: Path) -> List[Path]:
    """Finds all .py files, excluding common non-project dirs."""
    py_files = []
    for item in project_dir.rglob('*.py'):
        # Check if the file is within any excluded directory path
        is_excluded = False
        for exclude_dir in EXCLUDE_DIRS:
            try:
                # Check if the item's path relative to project_dir starts with an excluded dir
                relative_path = item.relative_to(project_dir)
                if relative_path.parts[0] == exclude_dir:
                    is_excluded = True
                    break
            except ValueError:
                 # Happens if item is not relative to project_dir (shouldn't with rglob)
                 pass
            except IndexError:
                 # Happens for files directly in project_dir
                 pass
        if not is_excluded:
            py_files.append(item)
    return py_files

def check_for_main_block(file_path: Path) -> bool:
    """Checks if a Python file likely contains a 'if __name__ == \"__main__\":' block."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            # Simple check, could be improved with regex for whitespace variations
            content = f.read()
            return 'if __name__ == "__main__":' in content or \
                   "if __name__ == '__main__':" in content
    except Exception as e:
        log.warning(f"Could not read file {file_path} to check for main block: {e}")
        return False

def prompt_yes_no(question: str, default_yes: bool = True) -> bool:
    """Asks a yes/no question and returns the boolean result."""
    suffix = "[Y/n]" if default_yes else "[y/N]"
    while True:
        ans = input(f"{question} {suffix} ").strip().lower()
        if not ans:
            return default_yes
        if ans in ['y', 'yes']:
            return True
        if ans in ['n', 'no']:
            return False
        echo(style("Please answer 'yes' or 'no'.", fg=colors.YELLOW))

def with_help_wrapper(label: str, func, *args, **kwargs):
    """
    Wrapper to run a function, capture its output/errors, and potentially
    pass context to the 'ask' command on failure.
    NOTE: This is simplified. Capturing stdout/stderr from a Python function
    directly requires redirecting sys.stdout/stderr, which is complex.
    This version focuses on wrapping subprocess calls via run_cmd.
    For direct Python calls, error handling should use try/except.
    Let's adapt run_cmd to potentially call 'ask' on failure.
    """
    # This concept is better applied directly within run_cmd or similar wrappers
    # if the goal is to capture external command output.
    # Replicating the exact bash 'with_help' behavior for arbitrary Python code
    # within the same process is non-trivial.
    # We'll rely on standard try/except for Python functions and enhance run_cmd.
    pass # See modified run_cmd/run_python_cmd if needed