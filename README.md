# pippy

*I don't feel like advertising anything today, come back later.*

---

## You probably want to find some other tool

Pippy does simple things for Python that other package managers and build tools do for other large programming languages and frameworks. As a member of the Spring team and a long-time developer of open source projects and reference architectures focused on developer experience, I wanted to create something that was useful for my own Python projects that let's me stay in my IDE without having to look up some obscure Python error or to struggle with getting an ML environment setup. I've got plans for this, but it will be a work in progress. Here are some things that ChatGPT wrote for you to get started.

### The AI wrote this, but also was essential in putting this little project together

- **One‑liner setup** – `curl | bash` or `pipx install git+https://github.com/you/pippy`.
- **Virtual‑env first** – `pippy init` always creates/activates `./.venv`.
- **Zero‑boilerplate deps** – `pippy install` auto‑generates *requirements.txt* with
  `pipreqs` and installs everything in one go.
- **Ask GPT without leaving the terminal** – `pippy ask "Python makes me want to pull my hair out but its me and not you, tell me how to get better at this..."` sends the last 50 lines of error + project context to OpenAI and prints an answer.
- **Handy day‑to‑day verbs** – `run`, `test`, `lock`, `format`, `lint`, `audit`,
  `ml` (TensorFlow sanity check) … all behind one command, which is useful for newbies coming to Python from other programming languages and framework technologies to get ML up and running on non-NVIDIA hardware and trying to use conda on the GPU with the best of intentions. You'll get the facts very quickly when stuff doesn't work for strange reasons with vague error messages.

pippy works on **Linux** and **macOS** (ships with only POSIX/BSD tools) and doesn’t require you to learn yet another package manager. Also, pippy isn't a package manager. It's a developer productivity tool for Python.

## I built this for myself

I know there are a lot of great CLI tools out there for Python, but I wanted something a little bit more extensible and flexible that follows the same patterns as both the Java (mvn/gradle) and Node (npm) patterns. Also, I really don't like how vague Python error outputs are, so I wanted to build in an AI helper that will jump in and explain Python errors that would otherwise require me to go to the browser and look something up. Now, when an error occurs, GPT will jump in and explain things in a few sentences that gets me back to staying productive.

### Don't use this tool

You should use better CLI tools for Python and go with production-grade open source projects that are popular and do similar things. As I keep developing Python applications and libraries, I'm going to improve this tool and make it better and better. Then you should use it.

So, if you've stumbled on this repository by some miracle or another, and you're interested in creating light-weight AI agent experiences with memory, project context, and task-based capabilities then drop me a note and let's work together on something.

---

## Quick start (not all of it is working yet)

```bash
# I recommend installing using pipx
pipx install git+https://github.com/kbastani/pippy
```

Initialize & install dependencies:

```bash
cd my-project
source pippy init   # initialize a venv in the current directory and use it
pippy install       # installs every dependency for every python file
pippy info          # tells you about your deps and your project structure
```

Run code & tests:

```bash
pippy run .         # runs the configured main or asks you to pick one (wip)
pippy test          # pytest if available, else unittest (works well)
```

Get AI help:

```bash
pippy ask "I can't install tensorflow using pip install tensorflow"
```

> ✨  First time you call `ask` you’ll be prompted for an OpenAI API key if it is not available already as an environment variable. (Will improve this over time)
>
> |   |
> | - |

---

## Command summary

| Command           | Description                                             |   |
| ----------------- | ------------------------------------------------------- | - |
| `init [dir]`      | Create & activate `.venv/` (default: cwd)               |   |
| `install [dir]`   | Generate + install requirements, configure **main**     |   |
| `update [dir]`    | Regenerate requirements & upgrade packages              |   |
| `run [file]`      | Run a `.py` file or choose from a list of runnable ones |   |
| `start`           | Alias for `pippy run .`                                 |   |
| `info`            | Show requirements + ASCII tree (excludes venv)          |   |
| `lock`            | `pip freeze` → *requirements.lock*                      |   |
| `test`            | Run `pytest` (or `unittest` fallback)                   |   |
| `clean`           | Remove `__pycache__` / `*.py[co]`                       |   |
| `shell`           | Spawn a subshell with venv activated                    |   |
| `ask [question]`  | Ask GPT with project context                            |   |
| `develop`         | `python -m pip install -e .`                            |   |
| `pkg`             | Build sdist + wheel (`python -m build`)                 |   |
| `publish`         | Upload *dist/* via `twine`                              |   |
| `lint` / `format` | `flake8` / `isort` + `black`                            |   |
| `audit`           | Security scan with `pip-audit`                          |   |
| `coverage`        | Run coverage report                                     |   |
| `docs init/build` | Sphinx scaffold & HTML build                            |   |
| `bump <level>`    | Bump version (patch/minor/major) – *TODO*               |   |
| `doctor`          | Quick environment health check                          |   |
| `ci-setup`        | CI scaffold stub                                        |   |
| `ml`              | TensorFlow install + device check                       |   |

---

## Installation internals

- `install_pippy.sh` copies the single **`pippy`** script into
  `/usr/local/bin` (or `$DESTDIR`) and sets the executable bit.
- No other files are required at runtime—Pippy is literally one Bash file.
- If run via `pipx`, the setup script drops a tiny Python shim that simply
  executes the bundled Bash file.

---

## Developing Pippy

```bash
# clone & hack
git clone https://github.com/kbastani/pippy
cd pippy
./pippy test        # run self‐tests (bats/shunit2)
./pippy lint        # shellcheck, shfmt, flake8
```

Pre‑commit hooks are configured; run `pre-commit install` after your first
clone.

---

## Roadmap

- Windows (Git‑bash / WSL) support
- Built‑in template for `pyproject.toml` scaffolding
- Homebrew formula + Chocolatey package

Don't create any PRs unless you want me to send you a 3D printed GitHub gold star. Check `CONTRIBUTING.md` for style & test guidelines (which was generated by AI so I didn't even read it).

---

## License

Whatever...