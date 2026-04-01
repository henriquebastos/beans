# Agent-oriented help/reference for `beans`

This is not a proposal to replace the normal `beans --help` output.
It is a reference for what agent-facing help should emphasize:
- the data model
- the most common workflow patterns
- the most common mistakes
- the fields and behaviors that are easy to misunderstand

## What agent-facing help should prioritize

### 1. Data model before command list
The parent/dependency distinction is the biggest conceptual trap.
Any richer help surface should explain this first.

### 2. Output behavior that surprises callers
Examples:
- whether `show` includes the body in text mode
- whether dependencies appear in text mode or JSON only
- field names in JSON (`parent_id`, `body`, `close_reason`)

### 3. Workflow patterns, not just syntax
Helpful sequences include:
- pick a ready bean
- read its full context
- claim it
- close it with a commit hash reason

### 4. Common mistakes
Examples worth documenting prominently:
- parent is not dependency
- `dep add` is separate from `update`
- brief text output vs detailed JSON output

## What should stay out of top-level help
The default `beans --help` output should remain concise.
It should not try to embed:
- the full data model spec
- multi-screen examples
- policy conventions
- long workflow tutorials

Those belong better in:
- README
- `beans recipe`
- a dedicated agent/workflow help surface

## Candidate future surfaces for this material

### Option A — expand `beans recipe`
Good fit if the audience is primarily coding agents.

### Option B — add `beans help agent`
Good fit if the project wants first-class agent-oriented help.

### Option C — improve README sections
Good fit for discoverability, but less convenient for CLI-only workflows.

## Recommended structure for richer help

If a richer help surface is added later, it should be structured like this:

1. Data model
2. Core workflows
3. Output behavior notes
4. Common mistakes
5. Command reference

## Non-goals
This document does not propose:
- changing the default `beans --help` into a multi-screen manual
- changing command behavior by itself
- freezing exact wording for future CLI output
