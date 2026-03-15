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
