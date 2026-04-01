# Beans Phase 2 — Implementation Specs

This document turns the Phase 2 roadmap into implementation-ready specs.
It focuses on:
- 2.2 `beans context <id>`
- 2.3 `beans subtree <id>`

`--body-file` is intentionally omitted here because it is already straightforward.

---

## 2.2 `beans context <id>`

## Goal
Return the selected bean plus its ancestor chain, so a caller can understand the task in one command.

## User problem
Today, understanding a bean often requires repeated manual calls:
- `beans show <id>`
- `beans show <parent>`
- `beans show <grandparent>`

This is repetitive and awkward for both humans and agents.

## Scope
Add a new command:

```bash
beans context <bean-id>
```

with two output modifiers:

```bash
beans context <bean-id> --json
beans context <bean-id> --brief
```

## Semantics
- Start from the selected bean.
- Follow `parent_id` upward until `null`.
- Include the selected bean as the first item.
- Order output from leaf to root.
- Fail if any referenced parent does not exist.
- Ignore dependencies entirely.
- Ignore children entirely.

This command is strictly about the ancestor chain.

## Output contract

### Text mode (default)
Detailed output with bodies.

Suggested shape:

```text
=== bean-2ef6f3c1 (task) ===
Title: Implement WebSocket bridge
Status: open
Priority: 1
Parent: bean-6df144ec
Assignee: claude

[body]

=== bean-6df144ec (epic) ===
Title: Live wiring
Status: open
Priority: 2
Parent: bean-e1f3fcdf
Assignee: none

[body]
```

Formatting requirements:
- blank line between entries
- stable header format
- print `Parent: none` or omit parent when null
- print `Assignee: none` when unassigned for readability

### `--brief`
One line per bean, no body.

Suggested shape:

```text
bean-2ef6f3c1  task     open        Implement WebSocket bridge
bean-6df144ec  epic     open        Live wiring
bean-e1f3fcdf  project  in_progress Petrus integration
```

### JSON mode
Return a JSON array ordered from leaf to root.
Each element should be the normal bean JSON object.

Example:

```json
[
  {
    "id": "bean-2ef6f3c1",
    "title": "Implement WebSocket bridge",
    "body": "...",
    "type": "task",
    "status": "open",
    "parent_id": "bean-6df144ec"
  },
  {
    "id": "bean-6df144ec",
    "title": "Live wiring",
    "body": "...",
    "type": "epic",
    "status": "open",
    "parent_id": "bean-e1f3fcdf"
  }
]
```

## API shape
Add a pure command API function in `api.py`, for example:

```python
def context_beans(store: Store, bean_id) -> list[Bean]:
    ...
```

Behavior:
- call `show_bean()` / `store.get()` iteratively
- accumulate beans until `parent_id is None`

## CLI shape
Add a new command in `cli.py`:

```python
@app.command()
def context(...):
    ...
```

Output handling:
- `--json` should go through the existing JSON output path
- `--brief` should be text-only
- reject `--brief` with `--json` if both are passed together

## Error behavior
- missing selected bean → existing not-found error behavior
- missing ancestor bean → same not-found error behavior
- no special casing for cycles required in V1
  - if desired, add a visited set for defensive protection

## Recommended tests

### API tests
- returns selected bean plus parent chain
- returns only selected bean when no parent exists
- raises on missing selected bean
- raises on missing ancestor bean

### CLI tests
- text output contains both leaf and parent titles
- `--brief` omits body text
- `--json` returns ordered array
- `--brief --json` is rejected

---

## 2.3 `beans subtree <id>`

## Goal
Return the descendant hierarchy under a bean, so callers can inspect subtree status without custom scripts.

## User problem
Users often want to answer:
- what is still open under this epic?
- are there any review beans under this task?
- what is the status summary of this subtree?

Today this requires ad hoc scripting.

## Scope
Add a new command:

```bash
beans subtree <bean-id>
```

with these modifiers:

```bash
beans subtree <bean-id> --open
beans subtree <bean-id> --summary
beans subtree <bean-id> --json
```

## Semantics
- Hierarchy is defined only by `parent_id`.
- Dependencies are ignored.
- The selected bean is the root.
- Descendants are all recursive children.
- Ordering should be stable and readable.

Recommended traversal order:
- depth-first pre-order

That produces intuitive tree output.

## Root handling
Recommendation:
- text mode: include the root as the first line
- JSON mode: include root separately from descendant items

This avoids ambiguity between the selected bean and its descendants.

## Output contract

### Default text mode
Indented tree.

Suggested shape:

```text
bean-aa6ec734  task     closed      Expose structured live Petrus snapshots
  bean-xyz123  review   open        Missing validation on payload shape
  bean-abc456  review   closed      Add edge case coverage
```

Required fields per line in V1:
- id
- type
- status
- title

Optional later fields:
- assignee
- priority

### `--open`
Show only non-closed nodes in the subtree.

Recommended V1 behavior:
- show only beans with status `open` or `in_progress`
- keep root line even if root is closed, so the subtree still has context

Example:

```text
bean-aa6ec734  task     closed      Expose structured live Petrus snapshots
  bean-xyz123  review   open        Missing validation on payload shape
```

If preserving full tree shape becomes awkward, a flat filtered output is acceptable for V1, but this should be documented.

### `--summary`
Aggregated counts only.

Suggested text shape:

```text
6 descendants: 4 closed, 1 open, 1 in_progress
by type: task=3, review=2, epic=1
```

Clarification:
- counts should exclude the root by default
- if root is included, say so explicitly

Recommendation: exclude root from summary counts.

### JSON mode
Suggested shape:

```json
{
  "root": {
    "id": "bean-aa6ec734",
    "title": "Expose structured live Petrus snapshots",
    "type": "task",
    "status": "closed"
  },
  "items": [
    {
      "depth": 1,
      "id": "bean-xyz123",
      "title": "Missing validation on payload shape",
      "type": "review",
      "status": "open",
      "parent_id": "bean-aa6ec734"
    },
    {
      "depth": 1,
      "id": "bean-abc456",
      "title": "Add edge case coverage",
      "type": "review",
      "status": "closed",
      "parent_id": "bean-aa6ec734"
    }
  ]
}
```

For `--summary --json`, suggested shape:

```json
{
  "root": {"id": "bean-aa6ec734", "title": "..."},
  "total": 6,
  "by_status": {"closed": 4, "open": 1, "in_progress": 1},
  "by_type": {"task": 3, "review": 2, "epic": 1}
}
```

## API shape
Add an API function, for example:

```python
def subtree_beans(store: Store, bean_id) -> tuple[Bean, list[tuple[int, Bean]]]:
    ...
```

or a clearer structure if preferred.

Requirements:
- load root bean first
- recursively gather descendants
- preserve traversal order
- annotate each descendant with depth for formatting

Possible implementation approaches:
1. do it in Python using `store.list()` and build parent→children index
2. do it in SQL with a recursive CTE

Recommendation for V1:
- use Python with a parent→children index
- simpler to reason about and test
- likely sufficient for current scale

## CLI behavior constraints
- `--summary` and `--open` should compose
- `--summary` and `--json` should compose
- plain `--json` returns tree items, not summary

## Error behavior
- missing root bean → existing not-found error behavior
- orphan descendants are irrelevant if they are not reachable from the root

## Recommended tests

### API tests
- returns root plus direct children
- returns recursive descendants with correct depth
- preserves stable traversal order
- `--open` equivalent filtering excludes closed descendants
- summary counts are correct

### CLI tests
- text output shows indentation
- `--open` hides closed descendants
- `--summary` prints counts only
- JSON output includes `root` and `items`
- summary JSON shape is correct

---

## Suggested order between 2.2 and 2.3

Implement in this order:
1. `context`
2. `subtree`

Reason:
- `context` is smaller and clearer
- it establishes a good pattern for a new read-only traversal command
- `subtree` has more output design choices and should follow once that pattern is in place
