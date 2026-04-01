# Beans Phase 3 — Visibility Improvement Specs

This document defines the next visibility-oriented improvements after Phase 2.
It focuses on:
- parent progress visibility
- better dependency visibility in text output
- a full-body text view that does not break existing defaults

---

## 3.1 Parent progress visibility

## Goal
Make it easy to see completion progress for beans that have children, especially epics and projects.

## User problem
Today, parent beans do not surface child completion progress.
To answer simple questions like:
- how many child beans are done?
- are any children still open?

users must count manually or script around the CLI.

## Non-goals
- Do not persist progress in the database.
- Do not add progress columns to the model.
- Do not compute dependency-based progress in V1.
- Do not attempt recursive rollups in V1.

V1 should be based on **direct children only**.

## Recommended behavior

### In `beans show <id>`
If the bean has direct children, show a progress line.

Minimal version:

```text
Progress: 3/6 children closed
```

Preferred version:

```text
Progress: 3/6 children closed (2 open, 1 in_progress)
```

Rules:
- if there are no direct children, omit the progress line entirely
- counts are based only on direct children
- child types do not matter in V1; all direct children count equally

### In `beans list`
Show a compact progress marker for beans that have direct children.

Suggested format:

```text
bean-6df144ec  epic  open  [3/6]  Live wiring
```

Rules:
- omit progress marker for beans with no direct children
- keep list output compact
- do not expand full status breakdown in list view

## JSON behavior
Recommendation:
- do not add progress fields to default JSON output in V1 unless needed for consistency
- if added, keep them clearly computed and named

Possible JSON extension later:

```json
{
  "child_progress": {
    "total": 6,
    "closed": 3,
    "open": 2,
    "in_progress": 1
  }
}
```

But this should only be added if it is useful enough to justify changing output shapes.

## API shape
Add helper(s) that compute child progress from existing store data.

For example:

```python
def child_progress(store: Store, bean_id) -> dict:
    ...
```

or a typed helper value.

Recommendation:
- compute from `store.list()` or a focused child query
- do not bury the logic in CLI formatting

## Recommended tests

### API / helper tests
- parent with no children → no progress / empty result
- parent with mixed child statuses → correct counts
- only direct children are counted
- grandchildren do not affect counts

### CLI tests
- `show` includes progress line when parent has children
- `show` omits progress line when there are no children
- `list` shows compact marker only for parents with children

---

## 3.2 Better dependency visibility in text output

## Goal
Make simple dependency questions answerable without switching to JSON.

## User problem
Dependency data exists, but text output makes it hard to answer:
- what blocks this bean?
- what does this bean block?

Today, users often have to rely on `--json show` or `graph`.

## Recommended behavior

### In `beans show <id>`
Add dependency lines to text output.

Suggested format:

```text
Blocked by: bean-a, bean-b
Blocks: bean-c
```

If empty:

```text
Blocked by: none
Blocks: none
```

Rules:
- keep values as bean IDs in V1
- do not inline titles yet
- keep output concise and stable

Why IDs first:
- simpler implementation
- easier to parse visually
- avoids extra formatting complexity

A later enhancement could include titles, for example:

```text
Blocked by:
  bean-a  Set up schema
  bean-b  Add auth layer
```

but not in V1.

### In `beans list`
Do not add dependency details in V1.
That would make list output noisy.

### Relation to `graph`
`graph` remains the dependency visualization tool.
This feature is only for quick local visibility in `show`.

## JSON behavior
Already good enough for now.
No change required in V1.

## API shape
Recommendation:
- expose dependency lookup in API helpers if not already convenient
- CLI should not manually query and compose too much

For example:

```python
def dependency_summary(store: Store, bean_id) -> dict[str, list[str]]:
    ...
```

Expected result:

```python
{"blocked_by": [...], "blocks": [...]}
```

## Recommended tests

### API / helper tests
- bean with no dependencies
- bean blocked by others
- bean blocking others
- bean with both directions

### CLI tests
- `show` prints `Blocked by: none` and `Blocks: none` when empty
- `show` prints IDs when dependencies exist
- output remains stable in text mode

---

## 3.3 Full-body text view without changing default `show`

## Goal
Provide a detailed text view for reading a bean body without forcing JSON mode, while preserving current default behavior.

## User problem
The brief text `show` output is convenient for summaries, but not for actually reading the bean body.
Switching to JSON just to read text is awkward for humans and noisy for agents when all they want is a detailed text view.

## Recommended behavior
Do **not** change the default behavior of:

```bash
beans show <id>
```

Instead, add an explicit detailed mode:

```bash
beans show <id> --full
```

## Text output contract for `--full`
Suggested format:

```text
bean-2ef6f3c1  task  open
Parent: bean-6df144ec
Assignee: claude
Priority: 1
Created: 2026-03-28T00:00:00Z
Closed: none
Blocked by: none
Blocks: bean-12345678

Goal:
...

Context:
...
```

Rules:
- body should appear exactly as stored
- metadata first, body after a blank line
- dependency visibility from 3.2 should be included here too
- if body is empty, show a clear placeholder or a trailing blank section

Recommendation for empty body:

```text
Body: <empty>
```

or:
- omit placeholder and just show no body content after metadata

Preferred: show `Body: <empty>` for clarity.

## Why `--full` is better than changing default `show`
- additive and safe
- avoids breaking existing habits or scripts
- keeps `show` useful for quick summary scanning
- gives a clear path for humans who want detail

## Relation to `context`
- `show --full` is for one bean
- `context` is for one bean plus ancestors

These two commands complement each other.

## JSON behavior
No change needed.
`--json show <id>` should continue returning the structured object.

## CLI constraints
- `--full` and `--json` should be mutually exclusive
- `--full` is text-mode only

## Recommended tests

### CLI tests
- `show --full` prints body content
- `show --full` includes key metadata lines
- `show --full` includes dependency lines
- `show --full --json` is rejected
- normal `show` remains unchanged

---

## Suggested implementation order inside Phase 3

1. Add dependency visibility to `show`
2. Add `show --full`
3. Add parent progress to `show`
4. Add parent progress to `list`

Reasoning:
- `show` improvements are easier to evaluate and less disruptive
- progress in `list` is the most output-sensitive change
- getting `show` right first provides a stable reference for later list formatting

---

## Open design decisions to settle before implementation

### 1. Should progress count all child types equally?
Recommendation: yes, in V1.

### 2. Should `show --full` display timestamps in raw ISO or formatted local time?
Recommendation: match current project conventions and keep it consistent with existing text output.

### 3. Should dependency lines show only IDs or IDs plus titles?
Recommendation: IDs only in V1.

### 4. Should progress appear in JSON output?
Recommendation: not in V1 unless there is a compelling use case.
