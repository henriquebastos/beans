# Beans — Agent Integration

This project uses [beans](https://github.com/henriquebastos/beans) for task tracking.
Beans is the primary tool for managing work — always use it to create, track, and
close tasks. Do not track work outside of beans.

## Before Starting Work

```bash
beans ready                     # see what's unblocked
beans show <id>                 # read the full bean before starting
beans claim <id> --actor <name> # claim it
```

## Self-Contained Beans

Every bean body must contain enough context for someone with no prior conversation to
pick it up. Include: what needs to change, why, which files are involved, and what
"done" looks like. Never rely on thread context or conversation history.

```bash
beans create "Title" --body "Full description of what needs to happen and why"
```

## Working on a Task

```bash
beans claim <id> --actor <name>   # claim before starting
# ... do the work ...
beans close <id>                  # close when done
```

If you discover new work while working on a bean, create a new bean for it:

```bash
beans create "New task discovered" --body "Description" --parent <epic-id>
beans dep add <blocker-id> <blocked-id>
```

## Bean Hygiene

- One bean per deliverable change
- Close beans when done, don't leave them dangling
- If a bean is no longer needed, close it with an update explaining why

## Commands Reference

| Command | Description |
|---------|-------------|
| `beans list` | List all beans |
| `beans ready` | List unblocked beans |
| `beans show <id>` | Show bean details |
| `beans create <title>` | Create a new bean |
| `beans update <id>` | Update bean fields |
| `beans close <id>` | Close a bean |
| `beans claim <id> --actor <name>` | Claim a bean |
| `beans release <id> --actor <name>` | Release a bean |
| `beans dep add <from> <to>` | Add dependency (from blocks to) |
| `beans dep remove <from> <to>` | Remove dependency |
| `beans schema` | Show JSON schemas for all models |

Use `--json` on any command for structured output. Use `--body` on create/update for descriptions.
