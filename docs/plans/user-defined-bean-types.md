# Plan: User-Defined Bean Types with Type-Prefixed IDs

## Goal

Allow users to define custom bean types in config. Bean IDs become `{type}-{hash}`
instead of `bean-{hash}`. Type semantics are up to the user — beans doesn't
enforce categories or meaning.

## Design Decisions

### 1. Type Definition Schema (in Config)

```python
class BeanType(BaseModel, frozen=True):
    name: str           # e.g. "epic", "story", "task", "bug", "spike", "review", "qa"
    description: str = ""  # optional human-readable description

class Config(BaseModel):
    path: Path = Field(exclude=True)
    projects: list[Project] = []
    types: list[BeanType] = []  # empty = use defaults
```

Types are simple names with optional descriptions. No categories or enforced semantics —
the user decides what types mean and how to organize them.

### 2. Default Types (baked into Config)

A new `Config` ships with `task`, `epic`, and `bug` as default types. No separate
`DEFAULT_TYPES` constant — the source of truth is always `config.types`:

```python
DEFAULT_TYPES = [
    BeanType(name="task"),
    BeanType(name="bug"),
    BeanType(name="epic"),
]

class Config(BaseModel):
    path: Path = Field(exclude=True)
    projects: list[Project] = []
    types: list[BeanType] = Field(default_factory=lambda: list(DEFAULT_TYPES))
```

Users add more types via `beans types add`. Existing configs without a `types` key
get the defaults on load. This preserves backward compatibility — existing users see
no change, and the API always has a types list to validate against.

### 3. BeanId Becomes Type-Prefixed

Currently: `bean-a3b4c5d6`
New: `task-a3b4c5d6`, `epic-12345678`, `review-deadbeef`

**BeanId changes:**

- `BeanId.generate(prefix)` already accepts a prefix — we just pass `{type}-` instead
  of `bean-`
- `BeanId.__new__` validation needs to accept **any known type prefix**, not just `bean-`
- This means BeanId validation becomes context-dependent (needs to know valid types)

**Approach:** Make `BeanId` accept any `word-hex` pattern by default. Strict validation
(is this type defined?) happens at the API/model layer, not in `BeanId` itself.

```python
class BeanId(str):
    pattern = re.compile(r"^[a-z]+-[0-9a-f]+$")

    def __new__(cls, value="", **kwargs):
        if not cls.pattern.match(value):
            raise ValueError(f"Invalid bean id: {value}")
        return super().__new__(cls, value)

    @classmethod
    def generate(cls, type_name="task") -> BeanId:
        return cls(f"{type_name}-{secrets.token_hex(ID_BYTES)}")

    @property
    def type_prefix(self) -> str:
        return self.split("-", 1)[0]
```

### 4. Bean Model Changes

Remove the hardcoded `Literal` for `type`. Replace with a plain `str` that defaults to
`"task"`:

```python
class Bean(BaseModel):
    id: BeanId = Field(default_factory=lambda: BeanId.generate("task"))
    type: str = "task"  # validated against config at API layer
    ...
```

**Why not validate in the model?** Because the model is pure — it shouldn't know about
config. Validation against the configured types list happens in `api.py` when
creating/updating beans.

### 5. API Layer Validation

Only `create_bean` validates types — updates don't re-validate (the type was valid at
creation time, and changing type is rare enough to not warrant guarding).

`create_bean` accepts a `valid_types` defaulting to empty tuple. When non-empty, the
type is validated. When empty, no validation happens. This keeps tests and scripts
frictionless while the CLI path gets validation for free via Config.

```python
def create_bean(store, title, valid_types=(), deps=(), **fields) -> Bean:
    bean_type = fields.get("type", "task")
    if valid_types and bean_type not in valid_types:
        raise ValueError(f"Unknown type: {bean_type}. Valid: {', '.join(sorted(valid_types))}")
    bean = Bean(title=title, id=BeanId.generate(bean_type), **fields)
    ...
```

The CLI extracts type names from `Config` and passes them through:

```python
# in CLI — rc is RunContext, rc.config is the Config object
valid = rc.config.type_names()  # -> {"task", "bug", "epic", ...}
create_bean(store, title, valid_types=valid, **fields)

# in tests / scripts — no config needed
create_bean(store, "Fix auth")  # no validation, just works
```

### 6. CLI Wiring — Config in RunContext

**Already done:** `RunContext` is now a `BaseModel` (not `NamedTuple`) with
`db: Path | None` and `Store.from_path` accepts `Path`. The variable is `rc`
(not `cfg`).

Remaining: add `config: Config` to `RunContext` and load it once in the `main`
callback:

```python
class RunContext(BaseModel):
    config: Config
    db: Path | None = None
    project: str | None = None
    json: bool = False
    dry_run: bool = False
    fields: list[str] | None = None

@app.callback()
def main(ctx: typer.Context, ...):
    config = Config.from_path(config_path())
    ctx.obj = RunContext(config=config, db=db, ...)
```

This gives us:
- **Valid types** from `rc.config.type_names()` — no separate function needed
- **`get_store` simplification** — `resolve_db` can use config directly instead of
  re-loading it internally
- **`config` command simplification** — just reads `rc.config` instead of loading again
- **Single load point** — config is read once per CLI invocation

### 7. Backward Compatibility & Migration

- **Existing `bean-*` IDs**: Still valid. `BeanId` accepts any `word-hex` pattern, so
  `bean-12345678` parses fine.
- **Existing databases**: No schema migration needed — `type` is already a TEXT column,
  `id` is TEXT.
- **Journal replay**: Old entries with `bean-` prefix work unchanged.
- **No forced migration**: Users keep `bean-*` IDs forever. New beans get `type-*` IDs.

### 8. New CLI Commands

```bash
# Manage types in config
beans types                    # list configured types (or defaults)
beans types add spike --description "Time-boxed investigation"
beans types remove spike
```

## Implementation Order (TDD)

1. **Config types model** — Add `BeanType` to `config.py`, test serialization
2. **BeanId accepts any type prefix** — Relax `BeanId` validation, update `generate()`,
   update tests
3. **Remove Literal from Bean.type** — Make it a plain `str`, update `BeanUpdate` too
4. **API validation against valid types** — Add type checking in `create_bean`
5. **Config in RunContext** — Add `config: Config` field, load once in CLI callback,
   simplify `get_store` and `config` command
6. **CLI wiring** — Pass valid types from config to `create_bean`
7. **`beans types` subcommand** — Add/remove/list types

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Breaking existing `bean-*` IDs | BeanId accepts any `word-hex` pattern — old IDs remain valid |
| Journal replay with mixed prefixes | Journal stores full snapshots — prefix is in the ID, no rewriting needed |
| Type typos in CLI | Validate against config and show available types in error message |
| Performance of category lookup | Types list is small (< 50); in-memory lookup is fine |

## Open Questions

1. **Should `BeanType` live in `models.py` or `config.py`?** — Leaning `config.py`
   since it's config-shaped, but it could go in `models.py` since Bean references it.
2. **Should `beans init` prompt for type setup?** — Or just use defaults until user runs
   `beans types add`?
