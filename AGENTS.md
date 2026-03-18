# Beans — Agent Guide

This file describes the conventions and design principles for contributing to beans.
Follow these closely — they are intentional and reflect the project's values.

## Philosophy

- **Low cognitive load.** Code reads top-to-bottom without jumping around.
- **Pure by default.** Push I/O to the boundary. Models and helpers are pure functions.
- **No over-engineering.** Don't build abstractions until you have two concrete uses.
- **Defer what you don't need.** If a feature isn't needed yet, don't add it.

## Architecture

```
src/beans/
├── models.py    # Pydantic models, pure functions, no I/O
├── store.py     # SQLite I/O boundary, BeanStore class
└── cli.py       # Typer CLI, thin wiring layer (parse → call → format)
```

- **models.py** — Pure data and pure functions. No imports from store or cli.
- **store.py** — The only place that touches the database. Accepts injected connections.
- **cli.py** — Thin wiring. No business logic. Display formatting lives here.

## Code Style

### No underscore prefixes

Everything is public. Don't use `_` to signal "private" — if it's in the module, it's
part of the module.

### Functions over methods

If it doesn't need `self`, it's a standalone function, not a method. Compose small
functions rather than building class hierarchies.

```python
# Yes
def columns(cursor):
    return [desc[0] for desc in cursor.description]

def row(cols, values):
    return dict(zip(cols, values))

# No
class BeanStore:
    def _get_columns(self, cursor): ...
    def _row_to_dict(self, cols, values): ...
```

### Default arguments for configurability

Never reference module-level constants directly inside function bodies. Instead, pass
them as default arguments. This makes functions testable and reusable without adding
configuration infrastructure. For classes, use class attributes instead of reaching for
the global.

```python
# Yes — constant flows through the signature
def find_beans_dir(start=None, dirname=BEANS_DIR) -> Path: ...

# Yes — class owns its configuration
class BeanId(str):
    prefix = ID_PREFIX
    def __new__(cls, value="", **kwargs):
        if not value.startswith(cls.prefix): ...

# No — function reaches for the global directly
def find_beans_dir(start=None) -> Path:
    candidate = current / BEANS_DIR  # hidden dependency
```

### `**kwargs` over dict for named fields

When a function accepts a set of named fields, use `**kwargs` instead of a dict parameter.
It reads better at the call site and lets the interpreter catch typos.

```python
# Yes
def update(self, bean_id, **fields) -> int: ...
store.update(bean_id, title="New title", status="closed")

# No
def update(self, bean_id, fields: dict) -> int: ...
store.update(bean_id, {"title": "New title", "status": "closed"})
```

### Constants for magic values

```python
ID_BYTES = 4
```

### Let Pydantic handle coercion

Don't manually convert what Pydantic validates and coerces automatically. For example,
Pydantic coerces ISO strings to datetime — don't call `fromisoformat()` yourself.

### Import organization

Use section comments and `force-sort-within-sections`:

```python
# Python imports
import json
import sqlite3

# Pip imports
import typer

# Internal imports
from beans.models import Bean
```

### Type annotations

Annotate return types. Don't annotate parameters when the default value tells the story.

## Dependency Injection

### Inject, don't construct

BeanStore takes a `sqlite3.Connection`, not a path. Factory classmethods handle
construction. This enables testing with `:memory:` databases.

```python
# Production
store = BeanStore.from_path("beans.db")

# Testing
store = BeanStore(sqlite3.connect(":memory:"))
```

### Context manager protocol

Resource-holding classes implement `__enter__`/`__exit__` to avoid explicit `close()`.

```python
with BeanStore.from_path("beans.db") as store:
    store.create(bean)
```

### Model stays pure, display lives in CLI

Don't add `__str__` or `__format__` to models for display purposes. Display formatting
is a CLI concern — use standalone functions like `format_bean()`.

## Testing

### No mocks

BeanStore gets a real SQLite `:memory:` database. Test real behavior, not mock wiring.

### Assert against the model, not individual fields

Leverage Pydantic equality to compare whole objects. Don't decompose into field-by-field
checks when a single comparison says it all.

```python
# Yes — one assertion, full structural check
assert store.get(bean.id) == bean
assert store.list() == [b1, b2]

# No — decomposing what equality already covers
result = store.get(bean.id)
assert result.id == bean.id
assert result.title == "Fix auth"
```

For model defaults, use `model_dump()` against an expected dict with fixed `id` and
`created_at` to pin dynamic fields.

```python
def test_defaults(self):
    bean = Bean(id="bean-00000000", title="Fix auth", created_at=FIXED_TIME)
    assert bean.model_dump() == {
        "id": "bean-00000000",
        "title": "Fix auth",
        "type": "task",
        ...
    }
```

### Module-level fixtures for shared infrastructure

Extract common fixtures (like `store`) to module level. Keep test classes for grouping
related tests by behavior, not for fixture scoping.

```python
@pytest.fixture()
def store():
    with BeanStore(sqlite3.connect(":memory:")) as s:
        yield s


class TestBeanStoreCreateAndList:
    def test_create_and_list(self, store):
        ...
```

### One assertion purpose per test

A test method can have multiple `assert` statements if they verify the same thing (e.g.,
a dict comparison). Don't test unrelated behaviors in one method.

### Readability over DRY

Allow repetition in tests. Each test should be self-contained and readable without
jumping to shared helpers.

## Workflow

### Red-green-refactor TDD

1. Write a failing test (RED)
2. Make it pass minimally (GREEN)
3. Commit: `feat: <description>`
4. Refactor, verify green
5. Commit: `refactor: <description>`

### Small commits

Each commit does one thing. Use conventional commit messages:

- `feat:` — new functionality
- `fix:` — bug fix
- `refactor:` — code improvement, no behavior change
- `chore:` — tooling, config, deps
- `docs:` — documentation
- `ci:` — CI/CD changes

### Verify before committing

```bash
uv run pytest
uv run ruff check src/ tests/
```

## Releasing

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
The package is `magic-beans` on PyPI, but the CLI is `beans` and the import is `import beans`.

## Tools

- **uv** — package management, running, building
- **pytest** — testing with coverage (`--cov=beans`)
- **ruff** — linting (line-length=120, select E,F,I,N,UP,RUF)
- **git-cliff** — changelog generation from conventional commits
