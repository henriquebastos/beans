## [0.4.1] - 2026-03-15

### 📚 Documentation

- Add release instructions to AGENTS.md
## [0.4.0] - 2026-03-15

### 🚀 Features

- Show bean by id
- Update bean fields
- Close bean
- Delete bean
- Id prefix matching
- Input validation
- BeanId type with validation on construction
- Use typer.Argument(parser=BeanId) for CLI bean_id validation
- Domain exceptions BeanNotFoundError and AmbiguousIdError
- Dependency storage
- Dependency CLI commands
- Ready graph query (pure)
- Ready query as recursive CTE
- Beans ready command
- Parent-child hierarchy
- Parent-child blocking in pure graph query
- Atomic claim
- Release claimed beans
- --dry-run for mutations
- Schema introspection command
- Error model and combined schema output
- Beans release --mine releases all claimed by actor

### 🐛 Bug Fixes

- Let homebrew action auto-detect download URL
- Rename prefix param to bean_id in resolve_id helper
- Claim is idempotent for same actor
- Release requires actor, idempotent when unclaimed
- Reject release with both bean id and --mine

### 💼 Other

- Phase 2 — bean CRUD

### 🚜 Refactor

- Extract output_bean helper to reduce repetition
- Move json/text logic into format_bean, remove output_bean
- Extract ID_PREFIX constant, remove magic string
- Rename prefix to bean_id in resolve_id
- Move generate_id to BeanId.generate classmethod
- Validate BeanId at CLI boundary, not in store
- Annotate resolve_id return type as BeanId
- Push id resolution into store, remove resolve_id from CLI
- Coerce to BeanId in resolve_id, CLI passes plain strings
- Extract BeanIdArg type alias
- Add opt() helper for readable typer.Option annotations
- Inline update fields dict with comprehension
- Remove resolve_id, get_bean handles prefix matching directly
- Delete_bean uses exact match and rowcount, no get_bean needed
- Use conn as context manager instead of explicit commit
- Simplify store to pure CRUD returning rowcounts
- Simplify roundtrip test with model equality
- Apply testing patterns and update AGENTS.md
- Update accepts **fields instead of dict
- Remove prefix matching, get uses exact id lookup
- Move value validation to CLI, keep field guard in store
- Rename bean_error to error, format_bean to line
- Introduce Dep model, replace raw tuples
- Replace line() with output() supporting beans, deps, lists, and json
- Output returns str, joins lists with newline
- Extract Bean.fields_validate for partial field validation
- Silence delete and dep remove output in json mode
- Introduce invoke_agent and invoke_human test fixtures
- Split store into Store, BeanStore, DepStore, MainStore
- Rename Store to BaseStore, MainStore to Store
- Remove unused AmbiguousIdError, fix from_path return type, move lifecycle to Store
- Extract rows() helper to simplify cursor-to-dict pattern
- DepStore.add takes a Dep model, consistent with BeanStore.create
- Claim and release reuse self.update
- Store.close uses self.conn directly for rollback

### 📚 Documentation

- Update CHANGELOG.md
- Add AGENTS.md with project conventions
- Add **kwargs over dict guideline to AGENTS.md

### ⚙️ Miscellaneous Tasks

- Opt into Node.js 24 for GitHub Actions
- Add MIT license file
- Add dist/ to gitignore
- Bump version to 0.4.0
## [0.1.1] - 2026-03-15

### 🐛 Bug Fixes

- Ruff isort config and import ordering
- Checkout main before committing changelog

### 📚 Documentation

- Add release instructions to README

### ⚙️ Miscellaneous Tasks

- Trigger release on GitHub Release publish
- Add git-cliff for changelog generation
- Auto-generate changelog on release
- Require passing tests before publish
- Reuse CI workflow in release pipeline
- Attach build artifacts to GitHub Release
- Auto-update Homebrew formula on release
- Bump version to 0.1.1
## [0.1.0] - 2026-03-15

### 🚀 Features

- Bean model with core fields
- Sqlite store with create and list
- Create and list CLI commands
- Display timestamps in local timezone
- Add context manager protocol to BeanStore

### 🚜 Refactor

- Extract row-to-bean conversion
- Inject conn into BeanStore, add from_path factory
- Extract _init_db method
- Move PRAGMAs into SCHEMA string
- Make init_db a public static method
- Extract columns() helper
- Drop manual created_at conversion, let pydantic coerce
- Drop labels field, defer to phase 8
- Extract row() helper
- Inline _row_to_bean into list_beans
- Drop underscore prefix from generate_bean_id
- Generalize generate_id with prefix and fn params
- Extract ID_BYTES constant
- Drop type annotations from generate_id params
- Restore return type annotation on generate_id
- Use from datetime import datetime
- Drop underscore prefixes from cli module
- Extract timestamp format as default arg
- Create bean before opening store
- Extract format_bean for display
- Extract dbfile fixture in CLI tests
- Consolidate bean defaults into single structural test
- Use fixed id and time for full structural comparison

### 📚 Documentation

- Add README with project motivation and usage
- Add coffee beans tagline

### ⚙️ Miscellaneous Tasks

- Initial repo with .gitignore and build plan
- Initialize project with uv
- Add TODO for project discovery
- Add pytest and ruff cache to gitignore
- Add CI and release workflows
- Rename package to magic-beans for PyPI
