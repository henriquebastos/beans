# Beans — Agent Integration

This project uses [beans](https://github.com/henriquebastos/beans) for issue tracking.

## Workflow

Before starting work, check for available tasks:

```bash
beans ready
```

Claim a task before working on it:

```bash
beans claim <bean-id> --actor <your-name>
```

When done, close the task:

```bash
beans close <bean-id>
```

## Commands Reference

| Command | Description |
|---------|-------------|
| `beans list` | List all beans |
| `beans ready` | List unblocked beans |
| `beans show <id>` | Show bean details |
| `beans create <title>` | Create a new bean |
| `beans update <id>` | Update bean fields |
| `beans close <id>` | Close a bean |
| `beans claim <id>` | Claim a bean |
| `beans release <id>` | Release a bean |
| `beans dep add <from> <to>` | Add dependency |
| `beans dep remove <from> <to>` | Remove dependency |
