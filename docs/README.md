# Beans docs roadmap

This directory contains the current planning and design documents for near-term CLI improvements.

## Documents

### `beans-improvement-proposals.md`
The cleaned roadmap.

Use this when you want:
- the prioritized list of open improvements
- the intended implementation order
- a high-level view of what is in scope and what was intentionally dropped

### `beans-phase-2-specs.md`
Implementation specs for the next high-value workflow features.

Covers:
- `beans context <id>`
- `beans subtree <id>`

Use this when you are ready to design or implement those commands.

### `beans-phase-3-specs.md`
Implementation specs for visibility improvements after Phase 2.

Covers:
- parent progress visibility
- better dependency visibility in text output
- `beans show --full`

Use this when Phase 2 is complete or when visibility improvements are being prioritized.

### `beans-ideal-help-output.md`
Agent-oriented help/reference notes.

This is not a literal proposal for replacing `beans --help`.
It captures what richer agent-facing help should emphasize:
- data model
- workflow patterns
- common mistakes
- surprising output behavior

## Recommended reading order

1. `beans-improvement-proposals.md`
2. `beans-phase-2-specs.md`
3. `beans-phase-3-specs.md`
4. `beans-ideal-help-output.md`

## Current recommended implementation order

1. `--body-file`
2. `beans context <id>`
3. `beans subtree <id>`
4. dependency visibility in `show`
5. `show --full`
6. parent progress in `show`
7. parent progress in `list`
8. `list --assignee`
