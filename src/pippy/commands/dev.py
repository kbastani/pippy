import typer
from pathlib import Path
from typing import Optional

from .. import helpers
from ..config import log

app = typer.Typer(help="Development workflow commands (build, publish, etc.).")

@app.command()
def develop(
    dir: Optional[Path] = typer.Argument(None, help="Project directory.", exists=True, file_okay=False, dir_okay=True, resolve_path=True)
):
    """Installs the project in editable mode (`pip install -e .`)."""
    project_dir = helpers.get_project_dir(dir)
    venv_path = helpers._ensure_venv(project_dir, create_if_missing=False)
    if not venv_path: return
    log.info("Installing project in editable mode...")
    try:
        helpers.run_pip_cmd(["install", "-e", "."], venv_path, project_dir, check=True)
        log.info("Editable install successful.")
    except typer.Exit:
        log.error("Editable install failed.")
        raise

@app.command("pkg")
def build_package(
    dir: Optional[Path] = typer.Argument(None, help="Project directory.", exists=True, file_okay=False, dir_okay=True, resolve_path=True)
):
    """Builds source and wheel distributions using 'python -m build'."""
    project_dir = helpers.get_project_dir(dir)
    venv_path = helpers._ensure_venv(project_dir, create_if_missing=False)
    if not venv_path: return

    log.info("Building distributions...")
    helpers.ensure_tool_installed("build", "build", venv_path, project_dir, check_import="build")

    try:
        # Use run_python_cmd to ensure it uses the venv's python
        helpers.run_python_cmd(["-m", "build"], venv_path, project_dir, check=True)
        log.info("Build successful. Distributions should be in 'dist/'.")
    except typer.Exit:
        log.error("Build failed.")
        raise

@app.command()
def publish(
    dir: Optional[Path] = typer.Argument(None, help="Project directory.", exists=True, file_okay=False, dir_okay=True, resolve_path=True),
    repository: Optional[str] = typer.Option(None, "--repository", "-r", help="PyPI repository URL (e.g., for testpypi).")
):
    """Uploads distributions from 'dist/' to PyPI using twine."""
    project_dir = helpers.get_project_dir(dir)
    venv_path = helpers._ensure_venv(project_dir, create_if_missing=False)
    if not venv_path: return

    dist_dir = project_dir / "dist"
    if not dist_dir.is_dir() or not any(dist_dir.iterdir()):
        log.error(f"'dist' directory not found or empty in {project_dir}.")
        log.info("Run 'pippy pkg' first.")
        raise typer.Exit(1)

    log.info("Uploading distributions via twine...")
    helpers.ensure_tool_installed("twine", "twine", venv_path, project_dir, check_command=["twine"])

    twine_cmd = helpers.get_executable(venv_path, "twine")
    cmd = [twine_cmd, "upload"]
    if repository:
         cmd.extend(["--repository-url", repository])
    cmd.append(str(dist_dir / "*")) # Glob pattern for twine

    # Handle 'python -m twine' case
    if " -m " in twine_cmd:
        python_exe, *module_args = twine_cmd.split(" ", 2)
        cmd = [python_exe.strip('"')] + module_args + cmd[1:]
        # Need shell=True if using '*' glob directly in the command string
        cmd_str = " ".join(cmd) # Convert list to string for shell=True
        log.debug(f"Running twine via shell: {cmd_str}")
        try:
             helpers.run_cmd(cmd_str, cwd=project_dir, check=True, shell=True)
        except typer.Exit:
             log.error("Twine upload failed.")
             raise
    else:
        # If twine_cmd is a direct path, shell=True is often needed for the glob '*'
        # Or use pathlib to find files and pass them explicitly? Safer.
        dist_files = [str(f) for f in dist_dir.glob('*') if f.is_file()]
        if not dist_files:
             log.error(f"No files found in {dist_dir} to upload.")
             raise typer.Exit(1)
        cmd = [twine_cmd, "upload"]
        if repository:
             cmd.extend(["--repository-url", repository])
        cmd.extend(dist_files)
        try:
             helpers.run_cmd(cmd, cwd=project_dir, check=True)
        except typer.Exit:
             log.error("Twine upload failed.")
             raise

    log.info("Upload command executed (check twine output for success).")


@app.command()
def bump(level: str = typer.Argument(..., help="Version level to bump: patch, minor, major.")):
    """Bumps the project version (Not Implemented Yet)."""
    log.warning("Version bumping is not yet implemented.")
    if level not in ["patch", "minor", "major"]:
        log.error("Invalid level. Choose 'patch', 'minor', or 'major'.")
        raise typer.Exit(1)
    # TODO: Implement logic to read pyproject.toml/setup.py, update version, write back
    raise typer.Exit(0) # Exit gracefully for now