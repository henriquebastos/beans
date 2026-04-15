# Beans — Agent Skill

This project uses beans for task tracking. Use beans commands to manage all work.

## Workflow

1. Check available work: `beans ready`
2. Read the bean: `beans show <id>`
3. Claim it: `beans claim <id> --actor <agent>`
4. Do the work
5. Close it: `beans close <id> --reason "Done in <commit>"`

## Key Commands

```bash
beans ready                              # see what's unblocked
beans show <id>                          # read the full bean
beans create "Title" --body "Desc"       # create a new bean
beans create "Title" --type bug          # create with specific type
beans claim <id> --actor <agent>         # claim before starting
beans close <id> --reason "Done"         # close when finished
beans --json list                        # list all beans as JSON
beans dep add <from> <to>               # add dependency
beans types                              # list available types
```

## Bean IDs

Bean IDs are prefixed with their type: `task-a3f2dd1c`, `epic-12345678`, `bug-deadbeef`.
Use `beans types` to see available types, `beans types add <name>` to add custom ones.

## Rules

- Always check `beans ready` before starting work.
- Claim a bean before working on it.
- One bean per deliverable change.
- Close beans when done — don't leave them dangling.
- If you discover new work, create a new bean for it.
- Append `#closes <bean-id>` to commit messages.
- Use `--json` for structured output when parsing programmatically.

## Autonomous Mode

When running autonomously, loop through ready beans:

```
beans ready → pick highest priority → beans claim →
read bean → implement → test → commit → beans close → next bean
```

## Structured Output

Use `beans --json <command>` for machine-readable output. The `beans schema` command
outputs JSON schemas for all models.
