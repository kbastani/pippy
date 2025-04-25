import typer

from .config import VERSION, APP_NAME
from .commands import core, qa, dev

app = typer.Typer(
    name=APP_NAME,
    help="pippy – lightweight project manager for Python.",
    add_completion=False, # Disable shell completion for simplicity initially
)

# Add command groups (subcommands)
app.add_typer(core.app, name="core", help=core.app.info.help)
app.add_typer(qa.app, name="qa") 
app.add_typer(dev.app, name="dev")

# Add top-level commands directly if preferred over groups
# e.g., @app.command("init") def main_init(...): core.init_project(...)
app.command("init")(core.init_project)
app.command("install")(core.install_deps)
app.command("run")(core.run_script)
app.command("start")(core.start_project)
app.command("lock")(core.lock_deps)
app.command("clean")(core.clean_pycache)
app.command("shell")(core.project_shell)
app.command("info")(core.project_info)
app.command("ask")(qa.ask_gpt)
# app.command("lint")(quality.lint_code)
# app.command("test")(quality.run_tests)
# app.command("format")(quality.format_code)
# app.command("check")(quality.check_code)
app.command("publish")(dev.publish)
app.command("pkg")(dev.build_package)
app.command("develop")(dev.develop)
# app.command("update")(misc.update_project)
# app.command("config")(misc.configure_project)
# app.command("status")(misc.check_status)
# app.command("help")(misc.show_help)
# app.command("version")(misc.show_version)
# app.command("docs")(misc.generate_docs)
# app.command("search")(misc.search_code)
# app.command("scan")(misc.scan_code)


def version_callback(value: bool):
    if value:
        typer.echo(f"{APP_NAME} version {VERSION}")
        raise typer.Exit()

@app.callback()
def main(
    version: bool = typer.Option(None, "--version", "-v", callback=version_callback, is_eager=True, help="Show version and exit."),
):
    """
    Pippy Entry Point
    """
    pass # Main callback can be used for global options/setup

if __name__ == "__main__":
    app()