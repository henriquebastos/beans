# Beans — GPT Integration

This project uses beans for task tracking. Always use beans commands to manage work.

## Setup

Include these instructions in your system prompt or custom instructions to enable
beans integration with GPT-based agents.

## Workflow

1. Run `beans ready` to see unblocked tasks
2. Run `beans show <id>` to read the full bean before starting
3. Run `beans claim <id> --actor gpt` to claim it
4. Implement the task
5. Run `beans close <id> --reason "Implemented in <commit>"` when done

## Key Commands

```bash
beans ready                          # see what's unblocked
beans show <id>                      # read the full bean
beans create "Title" --body "Desc"   # create a new bean
beans claim <id> --actor gpt         # claim before starting
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

## Function Calling

When using beans with function calling, prefer `--json` output on all commands
for reliable parsing. The `beans schema` command outputs JSON schemas for all models.
