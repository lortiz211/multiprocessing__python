# How Python Packaging Works — A Lesson From This Project

This is a read-top-to-bottom lesson, not a reference manual. Each section builds on
the previous one: we start with what a *module* is and end with why a *lockfile*
makes your project reproducible on any machine. Every concept is grounded in **this
repository's real files** (`pyproject.toml`, `uv.lock`, `.venv/`, `src/`), and most
sections end with a **▶ Try it** command you can run right now.

The mental model to hold onto throughout:

```
your source code  ──build──▶  a distribution (wheel)  ──publish──▶  an index (PyPI)
                                                                        │
your project  ◀──install into──  a virtual environment (.venv)  ◀──resolve+download──┘
                     ▲
                     └── described & pinned by pyproject.toml + uv.lock
```

`uv` is the single tool that drives every arrow in that diagram. We'll get to it —
but first, *why does any of this exist?*

---

## 1. Why packaging is hard

Writing Python that runs on *your* machine is easy. The hard problems all show up
the moment code has to live somewhere other than where you wrote it:

1. **Sharing code** — how does someone else get your program and run it?
2. **Dependencies** — your code uses libraries; those must come along too.
3. **Transitive dependencies** — your libraries have *their own* libraries, forming
   a graph that can be dozens deep.
4. **Version conflicts** — library A wants `requests>=2.30`, library B wants
   `requests<2.0`. Who wins? (This is "dependency hell.")
5. **Reproducibility** — "works on my machine" happens because your machine has an
   exact set of versions that nobody wrote down. A teammate installs *different*
   versions and hits a bug you can't reproduce.
6. **Isolation** — Project X needs Django 3, Project Y needs Django 5. They can't
   both use one global Python.

Every tool and file format in this lesson exists to solve one of those six problems.
Keep the list in mind; we'll tag each piece with the problem it kills.

---

## 2. The atoms: modules, packages, and imports

Before *distribution*, understand what Python is moving around.

- A **module** is a single `.py` file. `src/mpx/pipe.py` is the `pipe` module.
- A **package** is a directory of modules (traditionally with an `__init__.py`).
  `src/mpx/` is the `mpx` package; `src/chapt6/` is the `chapt6` package.
- **Importing** is Python finding and loading those files. When you write
  `from mpx.pipe import main`, Python searches a list of directories called
  `sys.path` for a `mpx/pipe.py`.

The key question is always: **how does `mpx` get onto `sys.path`?** That's the entire
job of installation — putting your code (and its dependencies) somewhere the
interpreter will look.

### Why the `src/` layout?

This project keeps code in `src/` (see `[tool.setuptools.packages.find] where =
["src"]` in `pyproject.toml`). Notice `src/` itself is *not* a package — `mpx` and
`chapt6` are. This is deliberate:

- Without `src/`, your project root is on `sys.path` automatically when you run
  Python there, so `import mpx` works *even if you never installed the project*.
  That hides packaging bugs — it works for you and breaks for everyone else.
- With `src/`, the only way `import mpx` works is if the project has actually been
  **installed** into your environment. So your local setup matches what a user gets.

> **Why it matters:** the `src/` layout forces you to test the *installed* form of
> your code, catching "I forgot to include that file" bugs before your users do.

▶ **Try it** — see the search path and confirm `mpx` is importable because it's installed:

```bash
uv run python -c "import sys; print(sys.path)"
uv run python -c "import mpx.pipe; print(mpx.pipe.__file__)"
```

---

## 3. Distributions: sdist vs wheel

You don't ship a folder of `.py` files to the world. You ship a **distribution** —
a single archive with your code plus metadata. There are two kinds:

| | **sdist** (source distribution) | **wheel** (built distribution) |
|---|---|---|
| Extension | `.tar.gz` | `.whl` |
| Contents | Source + build instructions | Pre-built, ready-to-drop-in files |
| Install step | Must be **built** on the user's machine first | **Unzipped** into place — no build |
| Speed | Slower | Fast |
| Platform | One archive for all | Often one **per platform** |

A wheel is "pre-cooked": installing it is basically unzipping into your environment.
An sdist is "raw ingredients": pip/uv must run the build backend (Section 6) to
produce a wheel first. Tools prefer wheels and fall back to sdists.

### See it in your own lockfile

Open `uv.lock` and look at the `ruff` entry. It lists **one sdist** and then **many
wheels**, one per operating system and CPU architecture:

```toml
[[package]]
name = "ruff"
version = "0.15.22"
source = { registry = "https://pypi.org/simple" }
sdist = { url = ".../ruff-0.15.22.tar.gz", hash = "sha256:3f15175b...", size = 4785063 }
wheels = [
    { url = ".../ruff-0.15.22-py3-none-macosx_11_0_arm64.whl", hash = "sha256:11c1c715...", ... },
    { url = ".../ruff-0.15.22-py3-none-win_amd64.whl",         hash = "sha256:9be63ba1...", ... },
    ...
]
```

Ruff ships per-platform wheels because it's a compiled Rust binary — the macOS-arm64
wheel contains a different binary than the Windows-x64 wheel. A pure-Python library,
by contrast, usually ships **one** wheel tagged `py3-none-any` that works everywhere.

> Read the wheel filename like a spec: `ruff-0.15.22-py3-none-macosx_11_0_arm64.whl`
> = *name*-*version*-*python tag*-*abi tag*-*platform tag*.

*(Solves: sharing code, reproducibility.)*

---

## 4. PyPI and the package index

Where do those URLs point? To an **index** — a server that hosts distributions. The
default is the **Python Package Index (PyPI)**. In your lock, every third-party
package says:

```toml
source = { registry = "https://pypi.org/simple" }
```

`/simple` is PyPI's machine-readable API (the "Simple Repository API"): give it a
package name, it returns the list of available files and their hashes. `uv add`,
`pip install`, etc. all talk to this endpoint.

### Integrity: those `sha256` hashes

Every `url` in the lock is paired with a `hash = "sha256:..."`. When uv downloads a
file, it recomputes the hash and refuses the file if it doesn't match. This protects
you from corrupted downloads *and* from a compromised mirror serving tampered files —
the lockfile is a signed manifest of exactly which bytes are allowed.

▶ **Try it** — inspect the metadata uv pulled from the index for an installed package
(and browse the index itself in a browser):

```bash
uv pip show ruff                  # name, version, and metadata from the index
# then open https://pypi.org/project/ruff/ to see the same package on the web
```

*(Solves: sharing code, reproducibility, supply-chain integrity.)*

---

## 5. Virtual environments — the isolation model

Here's the fix for problem #6 (isolation). A **virtual environment** is a
self-contained directory with its own copy/link of a Python interpreter and its own
`site-packages` folder where installed packages live. Your project has one at
`.venv/`.

The magic is just `sys.path` again. When you use a venv's Python, its own
`site-packages` is on the path instead of the global one:

```
                 ┌─────────────────────────────────────────┐
 uv run python   │  .venv/bin/python                        │
        │        │     sys.path includes:                   │
        └───────▶│       .venv/lib/python3.14/site-packages │ ◀── ruff, ty, and your
                 │       (NOT the system site-packages)      │     editable project live here
                 └─────────────────────────────────────────┘
```

So Project X's `.venv` can hold Django 3 while Project Y's `.venv` holds Django 5,
and they never see each other. The environment is **disposable**: delete `.venv/`
and rebuild it from `pyproject.toml` + `uv.lock` in seconds. That's why `.venv/` is
git-ignored (check `.gitignore`) — it's a *derived artifact*, not source.

> **Old way vs now:** you may have seen `python -m venv .venv` then
> `source .venv/bin/activate`. "Activating" just puts `.venv/bin` first on your
> shell `PATH`. `uv run` does the same thing *per command* without a persistent
> activation — no forgetting which env is active.

▶ **Try it** — prove which interpreter and site-packages are in play:

```bash
uv run python -c "import sys; print(sys.prefix)"        # -> .../.venv
uv run python -c "import ruff" 2>/dev/null && echo "ruff visible in venv"
```

*(Solves: isolation, version conflicts.)*

---

## 6. `pyproject.toml` — the single source of truth

Historically Python projects were configured by a scatter of files (`setup.py`,
`setup.cfg`, `requirements.txt`, `MANIFEST.in`, tool-specific dotfiles).
`pyproject.toml` (a standardized TOML file) replaced them with **one** declarative
file. Let's walk *your actual file*, section by section.

### `[project]` — standard metadata (PEP 621)

```toml
[project]
name = "multiprocessing-python"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = ">=3.14"
dependencies = []
```

- `name` / `version` — identity of your distribution.
- `requires-python = ">=3.14"` — a **gate**: tools refuse to install this into an
  older Python. (Your `.venv` is 3.14.)
- `dependencies` — your **runtime** requirements. Empty here because this project's
  code only uses the standard library. When you `uv add requests`, a
  `"requests>=..."` string lands in this list.

This block is a *standard* — any compliant tool (uv, pip, poetry, hatch) reads it
the same way.

### `[build-system]` — the build backend

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]
```

This answers "how do I turn `src/` into a wheel?" There are two roles:

- **Build frontend** — the tool a *user* runs (`uv build`, `pip install`). It
  doesn't know how to build *your* project specifically.
- **Build backend** — the library named here (`setuptools`) that actually collects
  your files and produces the sdist/wheel. `[tool.setuptools...]` configures it
  (here: "find packages under `src/`").

The frontend installs `requires` into a temporary environment, then calls the
backend. This split (PEP 517) is why you can swap setuptools for hatchling, flit,
or others without users changing how they install you.

### `[project.scripts]` — entry points

```toml
[project.scripts]
pipe = "mpx.pipe:main"
queues = "mpx.queues:main"
philo = "mpx.philosopher:runner"
```

This is how a library turns into a **command**. `pipe = "mpx.pipe:main"` means:
"when installed, create an executable named `pipe` that imports `mpx.pipe` and calls
its `main()` function." After install, `pipe` is a real command on your PATH.

▶ **Try it:**

```bash
uv run pipe          # runs mpx.pipe:main via the entry point
uv run philo         # runs mpx.philosopher:runner
```

### `[dependency-groups]` — dev-only dependencies (PEP 735)

```toml
[dependency-groups]
dev = [
    "ruff>=0.15",
    "ty>=0.0.60",
]
```

These are needed to *develop* the project but **not** to run it — linters, type
checkers, test runners. They are deliberately separate from `[project.dependencies]`
so that someone who just wants to *use* your package doesn't drag in your linter.
`uv sync` installs them by default; a production install can skip them with
`uv sync --no-dev`.

> **`dependencies` vs `dependency-groups`:** runtime vs development. Ask "does my
> code `import` this at runtime?" If yes → `dependencies`. If it's only tooling →
> a dependency group.

### `[tool.*]` — shared config for every tool

```toml
[tool.ruff.lint]
select = ["E", "F", "I", "ANN"]

[tool.ty.environment]
python = "./.venv"
```

Anything under `[tool.<name>]` is ignored by packaging and read by that specific
tool. This is why one file can configure ruff *and* ty *and* your build backend
without them stepping on each other.

*(Solves: sharing code, reproducibility, conflicts — it's the declaration of intent
that everything else acts on.)*

---

## 7. Dependency resolution and lockfiles

This is the heart of reproducibility, and the distinction most people miss.

- In `pyproject.toml` you **declare ranges**: `ty>=0.0.60` means "any version at or
  above 0.0.60 is acceptable." Ranges are flexible — good for *expressing intent*.
- But "any acceptable version" is not reproducible: install today and you get
  0.0.60; install next month and you get 0.1.0, which might behave differently.

**Resolution** is the process of walking the whole dependency graph and picking one
exact version of every package that satisfies *all* the range constraints
simultaneously (yours *and* every transitive dependency's). It's a constraint-solving
problem — genuinely hard, which is why a fast resolver matters.

A **lockfile** (`uv.lock`) is the *frozen result* of resolution: the exact version,
source, and hash of every package, for every platform. Look at yours:

```toml
[[package]]
name = "ty"
version = "0.0.60"                                  # exact, not a range
source = { registry = "https://pypi.org/simple" }
sdist = { url = "...", hash = "sha256:ebd7517d..." }
wheels = [ ... per-platform, each with its own sha256 ... ]

[package.metadata.requires-dev]
dev = [
    { name = "ruff", specifier = ">=0.15" },        # the *range* you declared
    { name = "ty",   specifier = ">=0.0.60" },
]
```

Notice both live in the lock: the **range you asked for** (`specifier`) and the
**exact version it resolved to** (`version`). That's the whole story of
reproducibility:

```
pyproject.toml (ranges)  ──uv lock──▶  uv.lock (exact pins + hashes)  ──uv sync──▶  .venv
   "I want ty >= 0.0.60"                 "everyone gets exactly 0.0.60"            (identical on every machine)
```

Commit `uv.lock` to git. A teammate runs `uv sync` and gets **byte-identical**
dependencies to yours — "works on my machine" is now "works on every machine."

▶ **Try it** — see the resolved graph and re-verify the lock without changing anything:

```bash
uv tree            # the resolved dependency graph
uv lock --check    # confirm uv.lock is up to date with pyproject.toml
```

*(Solves: reproducibility, transitive deps, version conflicts.)*

---

## 8. Where `uv` fits — and what it replaces

Everything so far — modules, wheels, PyPI, venvs, resolution, lockfiles — existed
before `uv`. The problem was that a *different tool* did each job, and they didn't
share state. `uv` is one fast (Rust) program that does all of it against the same
`pyproject.toml` + `uv.lock`:

| Job (concept from this lesson) | Old tool(s) | With uv |
|---|---|---|
| Install packages | `pip` | `uv add`, `uv sync` |
| Create/manage venvs (§5) | `venv`, `virtualenv` | automatic `.venv`, `uv venv` |
| Pin/lock deps (§7) | `pip-tools` (`pip-compile`) | `uv lock` (built in) |
| Install specific Pythons | `pyenv` | `uv python install` |
| Run CLI tools in isolation | `pipx` | `uv tool install`, `uvx` |
| Whole project management | `poetry`, `pdm` | `uv init/add/sync/build/publish` |
| Build distributions (§3) | `build` | `uv build` |
| Upload to PyPI (§4) | `twine` | `uv publish` |

You don't have to abandon the old names to understand uv — every uv command maps to
a concept you now know. `uv` just removes the seams between them.

---

## 9. The everyday uv workflow

Now the commands make sense, because each one is a concept from above:

```bash
# --- starting / structure ---
uv init                    # create pyproject.toml + basic project (§6)
uv python install 3.14     # download a specific interpreter (§5)
uv python pin 3.14         # write .python-version so the project uses it

# --- dependencies ---
uv add requests            # add a RUNTIME dep -> [project.dependencies] (§6), re-locks + syncs
uv add --dev ruff ty       # add a DEV dep -> [dependency-groups] (§6)
uv remove requests         # drop a dependency
uv lock                    # re-resolve ranges -> exact pins in uv.lock (§7)
uv sync                    # make .venv exactly match uv.lock (§5, §7)
uv sync --no-dev           # production install: skip dev groups

# --- running your code ---
uv run python script.py    # run inside the project's .venv, auto-syncing first (§5)
uv run pipe                # run a [project.scripts] entry point (§6)
uv run --with rich python  # run with an extra package, without adding it to the project

# --- inspecting ---
uv tree                    # resolved dependency graph (§7)
uv pip list                # what's installed in .venv

# --- tools (global CLIs, isolated from any project) ---
uv tool install ruff       # install a CLI on your PATH in its own env (like pipx)
uvx ruff check .           # run a tool one-off without installing (uv tool run)

# --- shipping a library (§3, §4, §10) ---
uv build                   # produce sdist + wheel in dist/
uv publish                 # upload dist/* to PyPI
```

> **Mental rule:** *declare* with `uv add`, *freeze* with `uv lock`, *materialize*
> with `uv sync`, *execute* with `uv run`. Most days you only touch `add` and `run`;
> uv locks and syncs for you automatically.

---

## 10. App vs library — which am I building?

The stack has two "output modes," and which one you're in tells you what to care
about:

- **An application** (a program you *run*): the important artifact is the **lockfile**.
  You want `uv sync` to reproduce an exact environment. You rarely `uv build` or
  publish. *This project is closer to this mode* — it's example/teaching code you run
  via `uv run pipe`, `uv run queues`, etc.
- **A library** (code others *import*): the important artifact is the **wheel** you
  publish to PyPI. The `[build-system]` and `[project]` metadata matter most, because
  strangers will build/install from them. Your lockfile is *not* published — a
  library must work across a *range* of dependency versions, so consumers resolve
  their own.

Interesting nuance: this project has a full `[build-system]`, so it's *buildable* as
a library, but its real use is as a runnable app. That's fine — the two modes aren't
exclusive.

▶ **Try it** — build this project into distributions and inspect them:

```bash
uv build
ls dist/          # multiprocessing_python-0.1.0.tar.gz  +  ...-py3-none-any.whl
```

---

## 11. Common pitfalls

- **Running the wrong Python.** `python script.py` may use your *system* Python, not
  the venv. Prefer `uv run python script.py` — it guarantees the project env.
- **Committing the wrong things.** Commit `pyproject.toml` **and** `uv.lock`. Never
  commit `.venv/` (it's a derived artifact, and it's git-ignored for that reason).
- **Confusing dependency kinds.** If your *code* imports it → `[project.dependencies]`.
  If it's only tooling/tests → `[dependency-groups]`. Getting this wrong bloats what
  your users install.
- **Editing `uv.lock` by hand.** Don't. Change `pyproject.toml`, then `uv lock`.
- **Editable installs surprise.** Your own project is installed *editable* (`source =
  { editable = "." }` in the lock) — edits to `src/` take effect immediately with no
  reinstall. But *adding a new entry point* to `[project.scripts]` does require a
  re-sync to create the command.
- **`requires-python` mismatch.** If a dependency needs a newer Python than your
  `requires-python` allows, resolution fails. The constraint is a feature, not a bug.

---

## 12. Glossary

- **Module** — a single `.py` file.
- **Package** — a directory of modules importable as one name.
- **Distribution** — a shippable archive of your project (sdist or wheel).
- **sdist** — source distribution (`.tar.gz`); must be built before install.
- **Wheel** — built distribution (`.whl`); installed by unzipping.
- **Index / PyPI** — server hosting distributions (`https://pypi.org/simple`).
- **Virtual environment (venv)** — isolated interpreter + `site-packages` (`.venv/`).
- **Build backend** — library that turns your source into a distribution
  (setuptools here); the **frontend** is the tool the user runs.
- **Resolver** — solves the dependency graph into one compatible version set.
- **Lockfile** — frozen, exact resolution result with hashes (`uv.lock`).
- **Entry point** — a name in `[project.scripts]` that becomes a CLI command.
- **Editable install** — your project linked (not copied) into the venv, so source
  edits apply instantly.
- **Extras** — optional dependency sets a package offers (e.g. `requests[socks]`).
- **Marker** — a conditional on a dependency (e.g. `; sys_platform == "win32"`).

---

## 13. Cheat-sheet

| I want to… | Command |
|---|---|
| Start a project | `uv init` |
| Add a runtime dependency | `uv add <pkg>` |
| Add a dev tool | `uv add --dev <pkg>` |
| Remove a dependency | `uv remove <pkg>` |
| Re-lock after editing pyproject | `uv lock` |
| Make `.venv` match the lock | `uv sync` |
| Production install (no dev) | `uv sync --no-dev` |
| Run a script in the env | `uv run python file.py` |
| Run an entry-point command | `uv run <name>` (e.g. `uv run pipe`) |
| Run with a one-off extra pkg | `uv run --with <pkg> python` |
| See the dependency tree | `uv tree` |
| Install a Python version | `uv python install 3.14` |
| Install a global CLI tool | `uv tool install <pkg>` / `uvx <pkg>` |
| Build sdist + wheel | `uv build` |
| Publish to PyPI | `uv publish` |

---

### Where to go next

- Run each **▶ Try it** block in order — seeing the output cements the model.
- Read your own `uv.lock` once, slowly, now that every field has meaning.
- Official docs: <https://docs.astral.sh/uv/> and the packaging guide at
  <https://packaging.python.org/>.
