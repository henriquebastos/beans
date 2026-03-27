## [0.5.1] - 2026-03-27

### 🚀 Features

- *(workspace)* Add MAGIC_BEANS_DIR env var override
- *(init)* Generate .gitignore in beans directory on init
- *(cli)* Add --priority flag to beans create
- *(cli)* Add --dep flag to beans create
- *(api)* Add reopen_bean() to clear closed fields on status change
- *(dep)* Prevent circular dependencies in beans dep add
- *(close)* Guard against closing a bean with open children
- *(list)* Add --type and --status filters to beans list
- *(ready)* Add --assignee and --unassigned filters to beans ready
- *(list,ready)* Add --parent filter to scope queries by parent bean
- *(show)* Include blocked_by and blocks in JSON output
- *(cli)* Add MAGIC_BEANS_PARENT_ID env var for default parent scoping
- *(create)* Validate parent bean exists before creation
- Add review bean type #closes bean-031d2faf

### 🚜 Refactor

- Address PR review feedback #closes bean-79860afc

### 📚 Documentation

- Update CHANGELOG.md

### ⚙️ Miscellaneous Tasks

- Sync uv.lock
## [0.5.0] - 2026-03-19

### 🚀 Features

- Phase 5 — Journal & Sync (#1)
- Phase 6 — Project Setup & Discovery (#2)
- Add --body flag to create command
- Add --reason flag to close command
- Add --parent flag to update command #closes bean-9c659aae
- Journal deps via triggers and restore on replay #closes bean-64955c3c
- Ready() returns beans ordered by priority #closes bean-efaa0197
- Ready() excludes closed beans #closes bean-77067a3f
- Validate Bean.type with Literal['task', 'bug', 'epic'] #closes bean-72f53d4c
- Add --type flag to create and update commands #closes bean-be7152e6
- Add global config, --type flag, and inspect-5p workflow #closes bean-d8d43fb4
- Agent integration recipes command #closes bean-59b77912
- Cross-project dependency tracking #closes bean-7c1acc31
- Beans search — full-text search across title and body #closes bean-a0dfb9e5
- Beans stats — aggregate counts by status, type, assignee #closes bean-fcda9235
- Beans graph — dependency tree visualization #closes bean-07d2eb8c
- --fields flag for filtering output columns #closes bean-b01406ae
- Labels — add, remove, filter by label in list/ready #closes bean-da4501e1
- Add schema versioning with PRAGMA user_version #closes bean-9ec929b9
- Expand api.py with missing operations and route cli.py through API layer
- Add DepNotFoundError for dependency operations #closes bean-02fe09c7
- Add list_deps wrapper in api.py #closes bean-7077b58c

### 🐛 Bug Fixes

- Ready() no longer propagates blocking through closed intermediate beans #closes bean-cbcdaf36
- Cascade-delete deps when deleting a bean #closes bean-b64b825c
- Dry-run rebuild no longer commits data through raw conn bypass #closes bean-d417f143
- Reject claiming a closed bean #closes bean-a3b2a258
- Scope --fields to --json mode only #closes bean-33c69b4a

### 🚜 Refactor

- Move find_beans_dir and project constants to project.py #closes bean-cab287e6
- Remove BaseStore inheritance, substores own their conn #closes bean-205d6e32
- Replace DryRunConnection proxy with autocommit transaction control #closes bean-b41a4538
- Replace fields_validate with BeanUpdate model #closes bean-02ba9ebd
- Extract claim/release to api.py, demote BeanStore to pure CRUD #closes bean-0472e890
- Replace journal triggers with app-level journaling #closes bean-4095cfba
- Replace module-level state dict with typer.Context #closes bean-ec781db2
- Make CLI commands thin wrappers over api functions #closes bean-f58060fb
- Remove cross-project deps, add project type
- Remove dead project-registry code from config.py #closes bean-ef3a672a
- Unify API functions to take Store instead of BeanStore/DepStore
- Simplify test_store.py and test_cli.py to layer-specific concerns
- Replace invoke_agent/invoke_human with cli/jcli fixtures in test_cli.py #closes bean-9ae804f6
- Move CliRunner inside cli fixture, remove module-level runner
- Use cli/jcli fixtures for rebuild tests instead of raw CliRunner
- Migrate dep tests to test_store.py, remove test_deps.py #closes bean-c1386db5
- Migrate recipe tests to test_cli.py, remove test_recipe.py #closes bean-e7849876
- Migrate graph tests to test_store.py and test_cli.py, remove test_graph.py #closes bean-598d1b87
- Migrate search tests to test_store.py and test_cli.py, remove test_search.py #closes bean-38353238
- Migrate stats tests to test_store.py and test_cli.py, remove test_stats.py #closes bean-e0f62d8f
- Move config CLI tests to test_cli.py, modernize test_config.py #closes bean-7771c208
- Rename project.py to workspace.py, modernize test_init.py fixtures #closes bean-e117807b
- Add Store delegation methods, simplify api.py calls #closes bean-2867fd1b
- Extract pure query functions and result mappers in store.py #closes bean-9e1db647

### 📚 Documentation

- Update CHANGELOG.md
- Add autonomous and collaborative agent workflow modes
- Comprehensive README with CLI reference and examples #closes bean-7feceebd
- Update README to reflect simplification #closes bean-b3679991

### 🧪 Testing

- Add fan-in dependency test for ready() #closes bean-a96c2d30
- Add CLI test for --body update #closes bean-f653e6e9
- Document BeanId accepts prefixes for matching #closes bean-26570e27

### ⚙️ Miscellaneous Tasks

- Document task tracking workflow with beans
- Delete dead graph.py superseded by SQL CTE #closes bean-1f175095
- Export beans journal for git-based sync
- Export beans journal for git-based sync
- Export beans journal for git-based sync
- Bump version to 0.5.0 #closes bean-2999fd08
## [0.4.1] - 2026-03-15

### 📚 Documentation

- Add release instructions to AGENTS.md

### ⚙️ Miscellaneous Tasks

- Bump version to 0.4.1
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
