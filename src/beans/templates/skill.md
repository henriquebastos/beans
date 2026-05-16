---
name: beans
description: Graph-based issue tracker for task coordination. Use when the project tracks work with beans — creating, querying, claiming, and closing tasks via CLI.
---

# Beans

Beans is a lightweight graph-based issue tracker for AI agent coordination. Beans are nodes;
dependencies are directed edges.

## Concepts

- **Bean**: a task-like item with `id`, `title`, `type`, `status`, `priority`, `body`,
  parent/assignee fields, and timestamps.
- **Bean IDs**: type-prefixed lowercase IDs such as `task-a3f2dd1c`, `bug-deadbeef`,
  `epic-12345678`.
- **Types**: configurable with `beans types`; defaults are `task`, `bug`, and `epic`.
  Creation validates configured types.
- **Status**: `open`, `in_progress`, or `closed`.
- **Priority**: integer `0..4`, where `0` is highest and default is `2`.
- **Dependencies**: `A blocks B` means B is not ready until A is closed.
- **Parent/child**: parent beans can contain child beans via `--parent`.
- **Ready**: a bean is ready when it is not closed, has no open blockers, and has no
  open children. Ready output is sorted by priority.

## Project discovery and storage

```bash
beans init                         # initialize using the project registry (default)
beans init --name <project-name>    # initialize registry project with explicit name
beans init --dir                   # create local .beans/ directory instead
beans migrate                      # migrate an existing .beans/ store to registry
beans migrate --name <project-name>
```

Command database resolution:

1. `--db PATH` uses an explicit SQLite database path.
2. `--project NAME` uses a named project from the registry.
3. Auto-discovery checks `MAGIC_BEANS_DIR`, then the registry, then walks upward for `.beans/`.

Related environment variables:

- `MAGIC_BEANS_DIR`: overrides beans store directory discovery.
- `MAGIC_BEANS_PARENT_ID`: supplies a default parent scope for `create`, `list`, and
  `ready`; explicit `--parent` overrides it.

## Commands

```bash
# Query
beans list                                        # all beans
beans list --type bug --status open               # filtered; comma-separated values allowed
beans list --parent <parent-id>                   # child beans for a parent
beans ready                                       # unblocked beans sorted by priority
beans ready --assignee alice                      # ready beans claimed by alice
beans ready --unassigned                          # ready unclaimed beans
beans ready --parent <parent-id>                  # ready children for a parent
beans show <id>                                   # show a single bean
beans search "query"                              # search title and body
beans stats                                       # counts by status, type, assignee
beans graph                                       # dependency tree visualization

# Create and update
beans create "Title"                              # new task
beans create "Title" --type bug --body "Details"  # explicit type and body
beans create "Title" --priority 0                 # highest priority
beans create "Title" --parent <parent-id>          # child bean
beans create "Title" --dep <blocker-id>            # inline dependency; repeat --dep as needed
beans update <id> --title "New" --priority 1 --body "Updated"
beans update <id> --status open                    # reopen closed bean and clear close fields
beans close <id> --reason "Fixed in abc1234"       # close with audit reason
beans close <id> --force                           # close even with open children
beans delete <id>                                  # delete a bean

# Assignment
beans claim <id> --actor <name>                    # sets assignee + in_progress
beans release <id> --actor <name>                  # clears assignee + open
beans release --mine --actor <name>                # release all claimed by actor

# Dependencies
beans dep add <blocker-id> <blocked-id>             # blocker must close before blocked
beans dep add <from-id> <to-id> --type blocks       # explicit dependency type
beans dep remove <from-id> <to-id>

# Types and config
beans types                                        # list configured types
beans types add spike --description "Investigation"
beans types remove spike
beans config                                       # show config path and settings
beans skill                                        # output this agent integration skill

# Structured output and safety
beans --json list                                  # JSON output
beans --json show <id>                             # JSON includes blocked_by and blocks arrays
beans --json --fields id,title,status list          # field filtering for JSON output
beans --json --fields id,title show <id>
beans --dry-run create "Try change"                # show result without persisting
beans schema                                       # JSON schemas for Bean, Dep, Error

# Journal and rebuild
beans export-journal > journal.jsonl                # export append-only change journal
beans rebuild journal.jsonl                         # replay journal into current database
```

## JSON notes

- `--json` makes command output machine-readable for successful command execution.
- `beans --json show <id>` adds dependency arrays: `blocked_by` and `blocks`.
- `--fields` is intended for JSON output and is most useful with `show`, `list`, `ready`,
  and `search`.
- Application-level errors under `--json` are shaped like `{"message": "..."}`; CLI
  parser errors may use Typer's normal error format.
