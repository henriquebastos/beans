---
name: beans
description: Graph-based issue tracker for task coordination. Use when the project tracks work with beans — creating, querying, claiming, and closing tasks via CLI.
---

# Beans

Graph-based issue tracker. Beans are nodes, dependencies are edges.

## Concepts

- **Bean**: a task with id, title, type, status, priority, body, and timestamps.
- **Bean IDs**: type-prefixed — `task-a3f2dd1c`, `epic-12345678`, `bug-deadbeef`.
- **Types**: configurable via `beans types`. Default: task, bug, epic.
- **Status**: open → in_progress → closed.
- **Dependencies**: `A blocks B` means B can't start until A is closed.
- **Parent/child**: epics contain subtasks via `--parent`.
- **Ready**: a bean is ready when all its blockers are closed and it has no open children.

## Commands

```bash
# Query
beans list                               # all beans
beans list --type bug --status open      # filtered
beans ready                              # unblocked beans, sorted by priority
beans show <id>                          # full details with deps
beans search "query"                     # search title and body
beans stats                              # counts by status, type, assignee
beans graph                              # dependency tree

# Create and update
beans create "Title"                     # new task
beans create "Title" --type bug --body "Details" --parent <epic-id>
beans update <id> --title "New" --priority 0 --body "Updated"
beans close <id> --reason "Fixed in abc1234"
beans delete <id>

# Assignment
beans claim <id> --actor <name>          # sets assignee + in_progress
beans release <id> --actor <name>        # clears assignee + open
beans release --mine --actor <name>      # release all claimed by actor

# Dependencies
beans dep add <blocker-id> <blocked-id>  # blocker must close before blocked
beans dep remove <from> <to>

# Types
beans types                              # list configured types
beans types add spike --description "Time-boxed investigation"
beans types remove spike

# Structured output
beans --json list                        # JSON output on any command
beans --json --fields id,title,status list
beans schema                             # JSON schemas for all models
```
