# Beans — Agent Integration

This project uses beans for task tracking. Use beans commands to manage all work.

## Workflow

1. Check available work: `beans ready`
2. Read the bean: `beans show <id>`
3. Claim it: `beans claim <id> --actor <name>`
4. Do the work
5. Close it: `beans close <id> --reason "Done in <commit>"`

## Key Commands

| Command | Description |
|---------|-------------|
| `beans ready` | List unblocked beans |
| `beans show <id>` | Show bean details |
| `beans create <title> --body <desc>` | Create a new bean |
| `beans close <id>` | Close a bean |
| `beans claim <id> --actor <name>` | Claim a bean |
| `beans list` | List all beans |
| `beans dep add <from> <to>` | Add dependency |

## Rules

- Always check `beans ready` before starting work.
- Claim a bean before working on it.
- One bean per deliverable change.
- Close beans when done — don't leave them dangling.
- If you discover new work, create a new bean for it.
- Use `--json` for structured output when integrating programmatically.
