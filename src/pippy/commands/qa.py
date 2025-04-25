import typer
from pathlib import Path
from typing import Optional, List
import sys
import os
import textwrap

# Ensure openai is installed or prompt user
try:
    import openai
except ImportError:
    # This check runs at import time. Better to check inside the command.
    openai = None


from .. import helpers
from ..config import log, OPENAI_API_KEY_ENV_VAR, EXCLUDE_DIRS, CONFIG_FILE_NAME

app = typer.Typer(help="AI-powered assistance for your project.")


def _ensure_openai_client(project_dir: Path, venv_path: Optional[Path]):
    """Checks for and installs openai if necessary, returns client."""
    if openai is None:
        helpers.ensure_tool_installed(
            tool_name="OpenAI Client",
            pip_package="openai>=1.3.0", # Pin to modern API
            venv_path=venv_path,
            project_dir=project_dir,
            check_import="openai"
        )
        # Re-import after potential installation
        import importlib
        globals()['openai'] = importlib.import_module("openai")
        if openai is None: # Should not happen if installation succeeded
             log.error("Failed to import OpenAI library even after attempting install.")
             raise typer.Exit(1)

    # --- API Key Handling (adapted from bash script) ---
    config = helpers.read_config(project_dir)
    use_env_key = config.get("use_env_key", False)
    saved_key = config.get("openai_api_key")
    env_key = os.environ.get(OPENAI_API_KEY_ENV_VAR)
    api_key = None

    if use_env_key:
        if not env_key:
            log.error(f"{OPENAI_API_KEY_ENV_VAR} is not set, but 'use_env_key' is true in {CONFIG_FILE_NAME}.")
            raise typer.Exit(1)
        api_key = env_key
        log.debug("Using OpenAI API key from environment variable.")
    elif saved_key:
        api_key = saved_key
        log.debug(f"Using OpenAI API key saved in {CONFIG_FILE_NAME}.")
    elif env_key:
        if helpers.prompt_yes_no(f"Use existing {OPENAI_API_KEY_ENV_VAR} from environment?", default_yes=True):
            api_key = env_key
            if helpers.prompt_yes_no(f"Save 'use_env_key: true' in {CONFIG_FILE_NAME}?", default_yes=True):
                 helpers.update_config_value(project_dir, "use_env_key", True)
    else:
        api_key = typer.prompt("Enter your OpenAI API Key", hide_input=True)
        if not api_key:
            log.error("No OpenAI API key provided.")
            raise typer.Exit(1)
        if helpers.prompt_yes_no(f"Save this key (masked) in {CONFIG_FILE_NAME}?", default_yes=True):
            helpers.update_config_value(project_dir, "openai_api_key", api_key)
            # DO NOT save use_env_key here

    if not api_key:
        log.error("Could not obtain OpenAI API Key.")
        raise typer.Exit(1)

    # The openai client uses the env var by default if key= argument is None
    os.environ[OPENAI_API_KEY_ENV_VAR] = api_key # Ensure it's set for the client
    try:
         # Test connection or instantiation early
         client = openai.OpenAI(api_key=api_key)
         # client.models.list() # Optional: Test API call
         return client
    except openai.AuthenticationError:
        log.error("OpenAI Authentication Error: Invalid API key provided.")
        # Optionally offer to clear saved key/config
        if saved_key or use_env_key:
             log.info(f"Consider checking/removing OpenAI settings in {CONFIG_FILE_NAME}.")
        raise typer.Exit(1)
    except Exception as e:
        log.error(f"Failed to initialize OpenAI client: {e}")
        raise typer.Exit(1)


@app.command("ask")
def ask_gpt(
    question_args: Optional[List[str]] = typer.Argument(None, help="Your question about the project. Reads from stdin if empty."),
    dir: Optional[Path] = typer.Option(None, "--dir", "-d", help="Project directory (default: current directory).", exists=True, file_okay=False, dir_okay=True, resolve_path=True),
    model: str = typer.Option("gpt-3.5-turbo", help="OpenAI model to use."),
    max_code_kb: int = typer.Option(200, help="Maximum KB of code context to send."),
):
    """Asks GPT-3.5/4 about your Python project code."""
    project_dir = helpers.get_project_dir(dir)
    # Venv isn't strictly required to *ask*, but might be for tool installation
    venv_path = helpers.find_venv(project_dir)

    client = _ensure_openai_client(project_dir, venv_path)

    # 1. Get the question
    question = ""
    if not sys.stdin.isatty(): # Check if stdin is piped
         question = sys.stdin.read().strip()
         log.info("Reading question from stdin...")
    if not question and question_args: # Check args only if stdin was empty/tty
        question = " ".join(question_args)
    if not question:
        question = typer.prompt("Question for GPT")

    if not question:
        log.error("No question provided.")
        raise typer.Exit(1)

    # 2. Collect project code context
    log.info("Collecting code context...")
    code_context = ""
    current_size = 0
    max_size = max_code_kb * 1024
    files_included = 0

    py_files = helpers.find_python_files(project_dir)

    for file_path in sorted(py_files):
        try:
            rel_path = file_path.relative_to(project_dir)
            file_content = file_path.read_text(encoding='utf-8', errors='ignore')
            snippet = f"### File: {rel_path}\n\n```python\n{file_content}\n```\n\n"
            snippet_size = len(snippet.encode('utf-8'))

            if current_size + snippet_size > max_size:
                log.warning(f"Code context limit ({max_code_kb} KB) reached. Truncating.")
                code_context += "\n... (truncated)\n"
                break

            code_context += snippet
            current_size += snippet_size
            files_included += 1
        except Exception as e:
            log.warning(f"Could not read or process file {file_path}: {e}")

    log.info(f"Included context from {files_included} files ({current_size / 1024:.1f} KB).")

    # 3. Call OpenAI API
    log.info(f"Sending request to OpenAI ({model})...")
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful Python project assistant. Analyze the provided code context to answer the user's question."},
                # Using user role for the main prompt is often better
                {"role": "user", "content": f"Project Code Context:\n\n{code_context}\n\n---\n\nQuestion: {question}"}
            ],
            temperature=0.5, # Adjust as needed
        )

        assistant_reply = response.choices[0].message.content.strip()

        typer.echo(helpers.style("\n--- GPT Response ---", bold=True))
        # Use textwrap for better formatting of long lines
        wrapped_reply = textwrap.fill(assistant_reply, width=100) # Adjust width
        typer.echo(wrapped_reply)
        typer.echo(helpers.style("--- End Response ---", bold=True))

    except openai.APIError as e:
         log.error(f"OpenAI API Error: {e}")
         # You can check e.status_code, e.request, etc.
         raise typer.Exit(1)
    except Exception as e:
         log.error(f"An error occurred during the OpenAI API call: {e}")
         raise typer.Exit(1)