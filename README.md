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
pip install magic-beans
```

Or with uv:

```bash
uv add magic-beans
```

## Quick start

```bash
# Initialize a project
beans init

# Create some beans
beans create "Set up database schema"
beans create "Build API endpoints" --type task
beans create "Write integration tests" --body "Cover all CRUD operations"

# Create an epic with children
beans create "Launch v1" --type epic
beans create "Deploy to staging" --parent bean-<epic-id>

# List all beans
beans list

# JSON output for agent consumption
beans --json list
```

## CLI Reference

### Global options

| Option | Description |
|---|---|
| `--json` | Output as JSON (for agents) |
| `--dry-run` | Show what would happen without writing |
| `--db PATH` | Use a specific SQLite database file |
| `--fields id,title,...` | Limit output to specific fields |
| `MAGIC_BEANS_DIR` | Environment variable: override `.beans/` directory discovery |

### Bean CRUD

```bash
# Create (types: task, bug, epic, project, review)
beans create "Fix auth" --type bug --body "Detailed description" --parent bean-<id>

# Show
beans show bean-a3f2dd1c

# Update
beans update bean-a3f2dd1c --title "New title" --status in_progress --priority 0

# Close (sets status=closed and closed_at)
beans close bean-a3f2dd1c --reason "Fixed in commit abc1234"

# Delete
beans delete bean-a3f2dd1c
```

### Querying

```bash
# List all beans
beans list

# List only unblocked beans (ready to work on)
beans ready

# Search by title and body
beans search "auth"

# Aggregate counts by status, type, assignee
beans stats

# Dependency tree visualization
beans graph
```

### Dependencies

```bash
# A blocks B (B can't start until A is closed)
beans dep add bean-aaaa bean-bbbb

# Remove a dependency
beans dep remove bean-aaaa bean-bbbb
```

### Agent coordination

```bash
# Claim a bean (sets assignee + status=in_progress)
beans claim bean-a3f2dd1c --actor alice

# Release a claimed bean
beans release bean-a3f2dd1c --actor alice

# Release all beans claimed by an actor
beans release --mine --actor alice
```

### Journal & sync

```bash
# Export journal to JSONL (for git-based sync)
beans export-journal > journal.jsonl

# Rebuild database from journal
beans rebuild journal.jsonl
```

### Configuration

```bash
# Show config path and settings
beans config

# Agent integration recipes
beans recipe --list
beans recipe claude
beans recipe generic
```

### Introspection

```bash
# Output JSON schemas for all models
beans schema

# Field filtering (works with show, list, ready, search)
beans --fields id,title,status list
beans --json --fields id,title show bean-a3f2dd1c
```

## Architecture

```
src/beans/
├── models.py    # Pydantic models (pure, no I/O)
├── store.py     # SQLite storage (I/O boundary)
├── api.py       # Command API (composes store calls)
├── config.py    # Global config (~/.config/beans/)
├── project.py   # Project discovery (find .beans/)
└── cli.py       # Typer CLI (thin wiring layer)
```

- **models.py** — Pure data. Bean is a Pydantic model with validation. No I/O, no side
  effects, easy to test.
- **store.py** — The I/O boundary. Store wraps a SQLite connection and composes
  BeanStore, DepStore, and JournalStore. Accepts an injected connection for testing.
- **api.py** — Command API. Each function is one use case (create, close, claim,
  release, stats, graph). Composes store calls.
- **cli.py** — Thin wiring. Parses args, calls API functions, formats output. No
  business logic.

## For AI agents

Beans is designed to be used by AI agents as a coordination mechanism. Add this to your
project's `AGENTS.md`, or use `beans recipe` for a ready-made integration:

```bash
beans recipe claude    # Claude/Amp recipe
beans recipe generic   # Generic agent recipe
```

Or add manually:

```markdown
## Task tracking

This project uses `beans` for task tracking. Use `beans --json` for all commands.

- Check available work: `beans --json ready`
- Claim a task: `beans claim <id> --actor <name>`
- Show task details: `beans --json show <id>`
- Mark done: `beans close <id> --reason "Implemented in <sha>"`
- Create subtasks: `beans create "<title>" --parent <id>`
- Add dependencies: `beans dep add <blocker-id> <blocked-id>`
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

1. Bump the version in `pyproject.toml`
2. Generate changelog:
   ```bash
   uv run git-cliff --tag v<VERSION> -o CHANGELOG.md
   ```
3. Commit and tag:
   ```bash
   git add pyproject.toml CHANGELOG.md
   git commit -m "chore: bump version to <VERSION>"
   git tag v<VERSION>
   git push origin main --tags
   ```
4. Create a GitHub Release:
   ```bash
   gh release create v<VERSION> --generate-notes
   ```

The release workflow runs tests, publishes to PyPI, and updates the Homebrew formula.
The package is published as `magic-beans` on PyPI (`pip install magic-beans`),
but the CLI command is `beans` and the import is `import beans`.
