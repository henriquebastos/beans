# Beans CLI — Prioritized Improvement Roadmap

This document keeps only open, realistic improvements.
Completed items are intentionally removed.
Large speculative ideas are intentionally removed.

## Principles

- Prefer features that remove repeated shell/Python glue.
- Prefer features that help both humans and agents.
- Prefer additive commands/flags over changing default output behavior.
- Avoid introducing new file formats or editor workflows unless simpler options fail.

---

## Phase 2 — High-value next features

## 2.1 `--body-file <path>`

### Problem
Detailed bean bodies are awkward to pass via shell quoting.
This hurts both `create` and `update`.

### Scope
Add file-based body input for:
- `beans create`
- `beans update`

### Proposed CLI

```bash
beans create "Title" --body-file /tmp/body.md
beans update bean-12345678 --body-file /tmp/body.md
```

### Semantics
- Reads the file as UTF-8 text.
- Uses the file contents exactly as the body.
- `--body` and `--body-file` are mutually exclusive.
- Empty files are allowed and set the body to `""`.

### Why this first
- Solves real friction immediately.
- Low design risk.
- Does not require changing other commands or output.

---

## 2.2 `beans context <id>`

### Problem
Understanding a bean often requires manually walking:
- the bean
- its parent
- its grandparent
- sometimes up to the project root

That means repeated `show` calls and repeated body extraction.

### Goal
Provide one command that returns the context chain from the selected bean up through all ancestors.

### Proposed CLI

```bash
beans context <bean-id>
beans context <bean-id> --json
beans context <bean-id> --brief
```

### Output shapes

#### Default text output
Detailed, body-first output ordered from leaf to root.

Example:

```text
=== bean-2ef6f3c1 (task) ===
Title: Implement WebSocket bridge
Status: open
Parent: bean-6df144ec

[full body]

=== bean-6df144ec (epic) ===
Title: Live wiring
Status: open
Parent: bean-e1f3fcdf

[full body]
```

#### `--brief`
One line per ancestor, no bodies.
Useful when the caller only needs the chain shape.

Example:

```text
bean-2ef6f3c1  task     open        Implement WebSocket bridge
bean-6df144ec  epic     open        Live wiring
bean-e1f3fcdf  project  in_progress Petrus integration
```

#### `--json`
JSON array ordered from leaf to root.
Each item is the full bean object.

Example shape:

```json
[
  {"id": "bean-2ef6f3c1", "title": "...", "body": "...", "parent_id": "bean-6df144ec"},
  {"id": "bean-6df144ec", "title": "...", "body": "...", "parent_id": "bean-e1f3fcdf"}
]
```

### Semantics
- Includes the selected bean as the first item.
- Walks `parent_id` until `null`.
- Fails if any referenced parent is missing.
- Does not include children or dependencies.
- This is strictly an ancestor-chain command.

### Why this is valuable
- Matches real session startup workflow.
- Reduces repeated `show` calls.
- Safe additive feature.

---

## 2.3 `beans subtree <id>`

### Problem
There is no built-in way to inspect the full descendant tree of a bean.
Users end up writing Python or shell one-liners to answer:
- what is still open under this epic?
- are there any open review beans under this task?
- what is the status of this subtree overall?

### Goal
Provide a command focused on descendants, not ancestors.

### Proposed CLI

```bash
beans subtree <bean-id>
beans subtree <bean-id> --open
beans subtree <bean-id> --summary
beans subtree <bean-id> --json
```

### V1 semantics
- Includes descendants only by default.
- Traverses by `parent_id` recursively.
- Tree order should be stable and readable.
- This command is about hierarchy only, not dependencies.

### Text output
Indented tree, one line per bean.

Example:

```text
bean-aa6ec734  task     closed      Expose structured live Petrus snapshots
  bean-xyz123  review   open        Missing validation on payload shape
  bean-abc456  review   closed      Add edge case coverage
```

Suggested fields per line:
- id
- type
- status
- title

Optional future enhancement:
- priority
- assignee

### `--open`
Show only open or in-progress descendants.
Still preserve indentation relative to the nearest shown ancestor if practical.
If preserving tree shape is too awkward in V1, flat output is acceptable as long as it is documented.

### `--summary`
Return aggregated subtree counts only.

Suggested text format:

```text
6 descendants: 4 closed, 1 open, 1 in_progress
by type: task=3, review=2, epic=1
```

Suggested JSON shape:

```json
{
  "total": 6,
  "by_status": {"closed": 4, "open": 1, "in_progress": 1},
  "by_type": {"task": 3, "review": 2, "epic": 1}
}
```

### `--json`
Return descendant beans as structured data.
Preferred shape for V1:

```json
{
  "root": {"id": "bean-aa6ec734", "title": "..."},
  "items": [
    {"depth": 1, "id": "bean-xyz123", "type": "review", "status": "open", "title": "..."},
    {"depth": 1, "id": "bean-abc456", "type": "review", "status": "closed", "title": "..."}
  ]
}
```

### Open design question
Should the root bean itself appear in default output?

Recommendation:
- text mode: show the root as the first line, then descendants indented beneath it
- JSON mode: keep root separate from `items`

That gives the best readability without confusing root vs descendants.

---

## 2.4 `beans list --assignee`

This is still a good idea, but it is lower priority than 2.1–2.3.

### Current state
`beans ready` already supports:
- `--assignee`
- `--unassigned`

`beans list` does not.

### Why it helps
Sometimes you want all beans for an assignee, not only ready ones.

### Proposed CLI

```bash
beans list --assignee claude
beans list --assignee claude --status open,in_progress
```

### Recommendation
Do this after 2.1–2.3 unless assignee filtering becomes a daily pain point.

---

## Phase 3 — Visibility improvements

These are good ideas, but they need tighter specs before implementation.

## 3.1 Parent progress in `show`/`list`

### Problem
Parent beans such as epics and projects do not show child completion progress.
Users must count children manually.

### Recommended scope
Add computed child progress for beans that have children.
Do not mutate stored data.
Do not add progress columns.

### Candidate behaviors

#### In `beans show <id>`
Add a progress line when the bean has children.

Example:

```text
Progress: 3/6 children closed
```

Optional richer form:

```text
Progress: 3/6 children closed (2 open, 1 in_progress)
```

#### In `beans list`
Show a compact progress marker only for beans with children.

Example:

```text
bean-6df144ec  epic  open  [3/6]  Live wiring
```

### Important constraints
- Progress should reflect direct children first.
- Recursive progress sounds attractive but is harder to reason about.
- Start with direct children only.

### Recommendation
Implement in this order:
1. `show`
2. `list`
3. only later consider recursive progress

---

## 3.2 Better dependency visibility in text output

### Problem
Dependency information exists, but text-mode visibility is weak.
You often need JSON output to answer simple dependency questions.

### Recommended scope
Improve text visibility without changing the meaning of existing commands.

### Candidate behaviors

#### `beans show <id>`
Add sections:

```text
Blocked by: bean-a, bean-b
Blocks: bean-c
```

If empty:

```text
Blocked by: none
Blocks: none
```

#### Optional future command
A focused dependency command may still be worthwhile later:

```bash
beans deps <id>
```

But `show` should improve first before adding a new command.

### Recommendation
Implement dependency visibility in `show` before creating any new dependency-inspection command.

---

## 3.3 Full-body text view

### Problem
`beans show` is currently brief in text mode, while the full body usually requires JSON output.
That is inconvenient, but changing the default may be disruptive.

### Recommended scope
Do not change `beans show` default behavior yet.
Instead add an explicit detailed mode.

### Candidate options

#### Option A — `beans show <id> --full`
This is the most conservative option.

#### Option B — `beans body <id>`
Very explicit, but introduces another command.

### Recommendation
Prefer:

```bash
beans show <id> --full
```

with text output like:

```text
bean-2ef6f3c1  task  open
Parent: bean-6df144ec
Assignee: claude
Created: 2026-03-28
Blocked by: none
Blocks: bean-123

[full body]
```

Why this over changing default `show` now:
- additive
- safer for scripts/habits
- still solves the reading problem

---

## Recommended implementation order

1. `--body-file`
2. `beans context <id>`
3. `beans subtree <id>`
4. parent progress in `show`
5. dependency visibility in text `show`
6. `show --full`
7. `list --assignee`
