# 🫘 Beans

**Graph-based issue tracker for AI agent coordination.**

Coding with AI makes developers absurdly productive. Coffee keeps them going.
Beans keep the whole loop fed. ☕

Beans is a lightweight, embedded issue tracker designed for AI agents to coordinate work
across tasks. It models issues as nodes in a dependency graph, backed by SQLite, with a
CLI that both humans and agents can use.

```
$ beans create "Fix auth middleware"
bean-a3f2dd1c  2025-06-15 10:42  Fix auth middleware

$ beans list
bean-a3f2dd1c  2025-06-15 10:42  Fix auth middleware
bean-7e2b9f01  2025-06-15 10:43  Add rate limiting

$ beans --json list
[{"id": "bean-a3f2dd1c", "title": "Fix auth middleware", "status": "open", ...}]
```

## Why Beans exists

Beans was born from analyzing [beads](https://github.com/steveyegge/beads), a
graph-based issue tracker with a similar goal: giving AI agents a structured way to
coordinate work. The idea is excellent. The execution, however, raised serious concerns.

### The problem with beads

Beads is invasive software that assumes too much about the user's intentions:

- **Curl-pipe-bash installer** that silently escalates to `sudo` to install a ~200MB
  binary system-wide
- **Strips macOS code signatures** and applies ad-hoc signatures to bypass Gatekeeper —
  the same technique used by actual malware
- **Installs 5 persistent git hooks** (`pre-commit`, `post-merge`, `pre-push`,
  `post-checkout`, `prepare-commit-msg`) that run on nearly every git operation
- **Runs a background database daemon** (Dolt SQL server) that binds to TCP ports
  3307/3308 — a MySQL-protocol server running on your machine
- **Silently modifies commit messages** by appending metadata trailers without asking
- **Auto-pushes data** to remote servers every 5 minutes
- **Fingerprints your machine** with unique UUIDs for the repo, clone, and project
- **Injects system prompts** into AI agent configuration files (e.g.,
  `.claude/settings.local.json`) to force agents to use the tool
- **Includes a "stealth mode"** that hides its presence from collaborators
- **Ships with telemetry** that records every command and all arguments, including who
  ran them

The core data model is a 50+ field struct covering everything from agent heartbeats to
ephemeral "wisps." It's not a simple tool — it's a complex system that assumes you want
all of it.

### What beans does differently

Beans keeps the good idea — a dependency graph for AI agent coordination — and throws
away everything else:

| | Beads | Beans |
|---|---|---|
| **Storage** | Dolt SQL server (~200MB, background daemon, TCP ports) | SQLite (zero-config, embedded, stdlib) |
| **Installation** | `curl \| bash` + `sudo` + signature stripping | `uv add beans` or `pip install beans` |
| **Git hooks** | 5 persistent hooks installed silently | None |
| **Commit modification** | Silent trailer injection | Never touches your commits |
| **Background processes** | Persistent MySQL-protocol daemon | None |
| **Network** | Opens TCP ports, auto-pushes every 5 min | Fully offline |
| **Telemetry** | OTel spans with actor identity + full args | None |
| **Stealth mode** | Yes, hides from collaborators | No — transparency is a feature |
| **AI config injection** | Writes to `.claude/settings.local.json` | Provides recipes you copy yourself |
| **Data model** | 50+ fields | ~10 fields + dependency edges |
| **Agent integration** | Forced via injected prompts | Opt-in via `AGENTS.md` instructions |

## Design principles

**Polite software.** Beans never modifies files without asking, never installs hooks,
never runs background processes, and never phones home. It's a CLI tool that reads and
writes to a local SQLite file. That's it.

**Embedded storage.** A single `.beans/beans.db` SQLite file with WAL mode. No servers,
no ports, no daemons. Works offline, works in CI, works anywhere Python runs.

**Graph-native.** Issues (beans) are nodes. Dependencies are typed edges. "What's ready
to work on?" is a graph query — show me all open beans with no open blockers.

**Agent-friendly.** The `--json` flag on every command makes beans machine-readable.
Agents don't need to parse human output. The CLI is a thin wrapper around a clean Python
API — agents can also use the library directly.

**Minimal by default.** A bean has an id, title, status, and timestamps. Everything else
is optional. No 50-field structs, no agent heartbeat tracking, no ephemeral wisps.

**Journal-based sync.** Changes are recorded in an append-only JSONL journal that can be
committed to git. The SQLite database is a materialized view that can be rebuilt from the
journal at any time. Sync through git, not through custom protocols.

## Installation

```bash
uv add beans
```

Or with pip:

```bash
pip install beans
```

## Quick start

```bash
# Create some beans
beans create "Set up database schema"
beans create "Build API endpoints"
beans create "Write integration tests"

# List all beans
beans list

# JSON output for agent consumption
beans --json list
```

## Architecture

```
src/beans/
├── models.py    # Pydantic models (pure, no I/O)
├── store.py     # SQLite storage (I/O boundary)
└── cli.py       # Typer CLI (thin wiring layer)
```

- **models.py** — Pure data. Bean is a Pydantic model with validation. No I/O, no side
  effects, easy to test.
- **store.py** — The I/O boundary. BeanStore wraps a SQLite connection with
  create/read/update/delete operations. Accepts an injected connection for testing.
- **cli.py** — Thin wiring. Parses args, calls store methods, formats output. No
  business logic.

## For AI agents

Beans is designed to be used by AI agents as a coordination mechanism. Add this to your
project's `AGENTS.md`:

```markdown
## Task tracking

This project uses `beans` for task tracking. Use `beans --json` for all commands.

- Check available work: `beans --json ready`
- Claim a task: `beans claim <id>`
- Mark done: `beans close <id>`
- Create subtasks: `beans create "<title>" --parent <id>`
```

## License

MIT

## Contributing

Beans is built with Python 3.14, managed with [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/henriquebastos/beans.git
cd beans
uv sync
uv run pytest
uv run ruff check src/ tests/
```

Tests use real SQLite `:memory:` databases — no mocks. The test suite runs in under a
second.

### Releasing

1. Bump the version:
   ```bash
   uv version --bump patch   # or minor, major
   ```

2. Commit and push:
   ```bash
   git add pyproject.toml uv.lock
   git commit -m "chore: bump version to $(uv version --short)"
   git push
   ```

3. Create a GitHub Release:
   ```bash
   gh release create v$(uv version --short) --generate-notes
   ```

This triggers the release workflow which:
- Runs the full test suite
- Generates changelog from conventional commits
- Updates `CHANGELOG.md` and commits it
- Attaches build artifacts to the release
- Publishes to PyPI

The package is published as `magic-beans` on PyPI (`pip install magic-beans`),
but the CLI command is `beans` and the import is `import beans`.
