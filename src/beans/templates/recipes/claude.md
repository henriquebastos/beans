# Beans — Claude Integration

This project uses beans for task tracking. Always use beans commands to manage work.

## Setup

Add this to your project's AGENTS.md or Claude instructions to enable beans integration.

## Workflow

1. Run `beans ready` to see unblocked tasks
2. Run `beans show <id>` to read the full bean before starting
3. Run `beans claim <id> --actor claude` to claim it
4. Implement the task
5. Run `beans close <id> --reason "Implemented in <commit>"` when done

## Key Commands

```bash
beans ready                          # see what's unblocked
beans show <id>                      # read the full bean
beans create "Title" --body "Desc"   # create a new bean
beans claim <id> --actor claude      # claim before starting
beans close <id> --reason "Done"     # close when finished
beans list --json                    # list all beans as JSON
beans dep add <from> <to>            # add dependency
```

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
