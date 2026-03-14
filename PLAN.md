# Beans — Build Plan

Graph-based issue tracker for AI agent coordination.
Built with Python 3.14, Typer, Pydantic, SQLite.

## Principles

- **Red-green-refactor**: write a failing test, make it pass, clean up
- **Tracer bullet**: simplest end-to-end first, then iterate
- **Small commits**: red-green-commit, refactor-green-commit
- **Semantic commit messages**: single line, conventional commits

---

## Phase 0: Project Skeleton

### 0.1 — Initialize uv project
- `uv init` with Python 3.14
- Add dependencies: typer, pydantic
- Add dev dependencies: pytest, pytest-cov, ruff, hypothesis, time-machine
- Create `src/beans/__init__.py`
- Create `tests/__init__.py`
- Configure pyproject.toml: ruff, pytest, project.scripts
- Verify: `uv run pytest` runs (no tests yet, exits clean)
- **commit**: `chore: initialize project with uv`

---

## Phase 1: Tracer Bullet — Create & List Beans

The goal is to establish all layers (model, store, CLI) with the simplest
possible feature: create a bean, list beans.

### 1.1 — Bean model
- RED: test that a Bean can be instantiated with id, title, type, status
- GREEN: create `models.py` with Bean Pydantic model (minimal fields:
  id, title, type, status, created_by, ref_id, created_at)
- **commit**: `feat: bean model with core fields`

### 1.2 — BeanStore.create and BeanStore.list
- RED: test create_bean stores a bean, list_beans returns it
- GREEN: create `store.py` with BeanStore class
  - `__init__(db_path)` opens SQLite connection with WAL mode
  - `create_bean(bean)` inserts into beans table
  - `list_beans()` returns all beans
  - Schema: single `beans` table matching the model
- **commit**: `feat: sqlite store with create and list`

### 1.3 — CLI create and list commands
- RED: test `beans create "Fix auth"` outputs the bean as JSON
- GREEN: create `cli.py` with Typer app
  - `beans create <title>` — creates bean, prints result
  - `beans list` — lists all beans
  - `--json` global flag for structured output
  - Wire BeanStore with project discovery (find `.beans/` walking up)
- **commit**: `feat: create and list CLI commands`

### 1.4 — Tracer bullet refactor
- Review naming, layers, API surface
- Ensure tests read clearly
- **commit**: `refactor: clean up tracer bullet`

---

## Phase 2: Bean CRUD

### 2.1 — Show a bean
- RED: test show returns a bean by id (full or prefix match)
- GREEN: `BeanStore.get_bean(id)` + `beans show <id>`
- **commit**: `feat: show bean by id`

### 2.2 — Update a bean
- RED: test update changes title, status, priority, labels
- GREEN: `BeanStore.update_bean(id, fields)` + `beans update <id>`
- **commit**: `feat: update bean fields`

### 2.3 — Close a bean
- RED: test close sets status=closed and closed_at
- GREEN: `beans close <id>` (convenience for update --status closed)
- **commit**: `feat: close bean`

### 2.4 — Delete a bean
- RED: test delete removes bean from store
- GREEN: `BeanStore.delete_bean(id)` + `beans delete <id>`
- **commit**: `feat: delete bean`

### 2.5 — ID prefix matching
- RED: test that `bean-a3` matches `bean-a3f2dd1c` when unique
- RED: test ambiguous prefix returns error
- GREEN: implement prefix lookup in store
- **commit**: `feat: id prefix matching`

### 2.6 — Input validation
- RED: test invalid id format rejected
- RED: test invalid status rejected
- GREEN: validate in store/CLI layer
- **commit**: `feat: input validation`

---

## Phase 3: Dependencies & Graph

### 3.1 — Dependencies table
- RED: test add_dependency stores an edge between two beans
- GREEN: `dependencies` table, `BeanStore.add_dependency(from, to, type)`
- **commit**: `feat: dependency storage`

### 3.2 — Add and remove dependency CLI
- RED: test `beans dep add <id> <blocks> --type blocks`
- GREEN: `beans dep add`, `beans dep remove`
- **commit**: `feat: dependency CLI commands`

### 3.3 — Ready query (pure function)
- RED: test ready returns only unblocked beans
- RED: test transitive blocking excluded
- RED: test closed blockers don't block
- GREEN: `graph.ready(beans, deps)` pure function
- **commit**: `feat: ready graph query (pure)`

### 3.4 — Ready query (SQL)
- RED: test BeanStore.ready_beans() returns unblocked beans
- GREEN: recursive CTE in store
- **commit**: `feat: ready query as recursive CTE`

### 3.5 — Ready CLI
- RED: test `beans ready` lists only unblocked beans
- GREEN: `beans ready` command
- **commit**: `feat: beans ready command`

### 3.6 — Parent-child hierarchy
- RED: test creating bean with --parent sets parent_id
- RED: test parent blocks if it has open children
- GREEN: hierarchical ID generation (parent.N)
- **commit**: `feat: parent-child hierarchy`

---

## Phase 4: Agent Coordination

### 4.1 — Claim a bean
- RED: test claim sets assignee + status=in_progress atomically
- RED: test claiming already-claimed bean fails
- GREEN: `BeanStore.claim_bean(id, actor)` + `beans claim <id>`
- **commit**: `feat: atomic claim`

### 4.2 — Release a bean
- RED: test release clears assignee, sets status back to open
- GREEN: `beans release <id>`, `beans release --mine`
- **commit**: `feat: release claimed beans`

### 4.3 — JSON output mode
- RED: test every command outputs valid JSON with --json
- GREEN: global `--json` callback, consistent output format
- **commit**: `feat: consistent --json output`

### 4.4 — Dry-run mode
- RED: test --dry-run shows what would happen without writing
- GREEN: global `--dry-run` flag
- **commit**: `feat: --dry-run for mutations`

### 4.5 — Schema introspection
- RED: test `beans schema` outputs JSON schema
- GREEN: `beans schema` using Bean.model_json_schema()
- **commit**: `feat: schema introspection command`

---

## Phase 5: Journal & Sync

### 5.1 — Journal table with triggers
- RED: test that creating a bean also creates a journal entry
- GREEN: journal table + AFTER INSERT trigger on beans
- **commit**: `feat: journal table with create trigger`

### 5.2 — Journal triggers for update and delete
- RED: test update and delete create journal entries
- GREEN: AFTER UPDATE and AFTER DELETE triggers
- **commit**: `feat: journal triggers for update and delete`

### 5.3 — Export journal to JSONL
- RED: test export produces valid JSONL
- GREEN: `journal.py` export function + `beans export-journal`
- **commit**: `feat: export journal to JSONL`

### 5.4 — Import and replay journal
- RED: test replay rebuilds database from JSONL
- GREEN: `journal.py` replay function + `beans rebuild`
- **commit**: `feat: rebuild database from journal`

---

## Phase 6: Project Setup & Discovery

### 6.1 — beans init
- RED: test init creates .beans/ directory with db and config
- GREEN: `beans init` command
  - Creates .beans/, initializes db, copies default AGENTS.md
  - Prints reference command for project AGENTS.md
  - Asks before modifying project files
- **commit**: `feat: beans init`

### 6.2 — Project discovery
- RED: test finds .beans/ walking up from subdirectory
- RED: test error when no .beans/ found
- GREEN: `find_beans_dir()` in store.py
- **commit**: `feat: project discovery walking up from cwd`

### 6.3 — Default AGENTS.md
- RED: test init creates .beans/AGENTS.md from template
- GREEN: ship default template in package
- **commit**: `feat: default AGENTS.md template`

---

## Phase 7: Recipes & Config

### 7.1 — Global config
- RED: test config reads from ~/.config/beans/config.json
- GREEN: `beans config` command, XDG path resolution
- **commit**: `feat: global config at ~/.config/beans/`

### 7.2 — Agent recipes
- RED: test `beans recipe claude` outputs valid instructions
- GREEN: `beans recipe <client>` command with bundled recipes
- **commit**: `feat: agent integration recipes`

### 7.3 — Cross-project dependencies
- RED: test cross-project dep links beans across projects
- GREEN: projects.json registry, cross-deps.json
- **commit**: `feat: cross-project dependency tracking`

---

## Phase 8: Polish

### 8.1 — beans search
- Full-text search across title, body, labels

### 8.2 — beans stats
- Aggregate counts by status, type, assignee

### 8.3 — beans graph
- Dependency tree visualization (text-based)

### 8.4 — Field filtering
- `--fields id,title,status` to limit output

### 8.5 — Labels
- `beans label add <id> <label>`, `beans label remove`
- Filter by label in list/ready

### 8.6 — README
- Usage docs, examples, philosophy
