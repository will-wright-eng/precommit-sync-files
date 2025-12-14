# precommit-sync-files — Design Document

## 1. Overview

**precommit-sync-files** is a reusable, published `pre-commit` hook repository that ensures a set of *common, canonical files* remain synchronized across multiple Git repositories.

The hook is designed to:

* Detect configuration or policy drift early (pre-commit / CI)
* Provide a safe, opt-in mechanism for syncing shared files
* Act as lightweight governance without forcing a monorepo

Typical synced files include:

* CI workflows (`.github/workflows/*.yml`)
* Formatting / lint configs
* License headers
* Security policies
* Base `pyproject.toml` or tooling config

---

## 2. Goals & Non-Goals

### Goals

* ✅ Reusable across many repositories
* ✅ Deterministic and reproducible
* ✅ Safe by default (no silent overwrites)
* ✅ CI-friendly (check-only mode)
* ✅ Simple TOML-based configuration
* ✅ Zero external dependencies (uses only Python standard library)

### Non-Goals

* ❌ Two-way merge or conflict resolution
* ❌ Automatic syncing without explicit opt-in
* ❌ Acting as a full templating engine (initially)
* ❌ Replacing Git submodules or monorepos

---

## 3. User Experience

### Opt-in Model

Repositories explicitly opt in by adding a configuration file:

```
.sync-files.toml
```

If the file does not exist, the hook is a no-op.

---

### Typical Developer Flow

1. Developer clones repo
2. Runs `pre-commit install`
3. Makes changes
4. On commit:

   * Hook checks synced files
   * Fails if drift is detected
5. Developer either:

   * Updates local file to match canonical source, or
   * Runs hook in `--write` mode to auto-sync

---

## 4. Configuration Specification

### `.sync-files.toml`

```toml
[source]
repo = "https://github.com/will-wright-eng/precommit-sync-files"
ref = "main"

[[files]]
src = ".github/workflows/ci.yaml"
dst = ".github/workflows/ci.yaml"

[[files]]
src = "pyproject.toml"
dst = "pyproject.toml"

[options]
mode = "check"  # "check" | "write" (default: "check")
```

### Field Definitions

| Field          | Description                               |
| -------------- | ----------------------------------------- |
| `source.repo`  | Git repository containing canonical files |
| `source.ref`   | Branch, tag, or commit SHA                |
| `files[].src`  | Path inside source repo                   |
| `files[].dst`  | Path inside consuming repo                |
| `options.mode` | Default execution mode                    |

---

## 5. Hook Interface

### pre-commit Hook Definition

```yaml
- id: sync-common-files
  name: Sync common files across repos
  entry: sync-common-files
  language: python
  pass_filenames: false
```

### CLI Interface

```
sync-common-files [--write]
```

| Flag      | Behavior                                 |
| --------- | ---------------------------------------- |
| `--write` | Overwrite local files instead of failing |

---

## 6. System Architecture

### High-Level Flow

```
┌────────────┐
│ pre-commit │
└─────┬──────┘
      │
      ▼
┌──────────────┐
│ CLI Entrypoint│
└─────┬────────┘
      │
      ▼
┌────────────────────┐
│ Load .sync-files.toml │
└─────┬──────────────┘
      │
      ▼
┌────────────────────┐
│ Fetch source repo   │
└─────┬──────────────┘
      │
      ▼
┌────────────────────┐
│ Compare file hashes │
└─────┬──────────────┘
      │
      ▼
┌──────────────────────────┐
│ Fail OR Write differences │
└──────────────────────────┘
```

---

## 7. Core Components

### 7.1 CLI Layer (`cli.py`)

Responsibilities:

* Parse flags (`--write`)
* Invoke sync engine
* Return correct exit code

No business logic.

---

### 7.2 Sync Engine (`sync.py`)

Responsibilities:

* Load and validate configuration
* Fetch canonical source
* Compare content using hashes
* Enforce execution mode

Key design decisions:

* Hash comparison (SHA-256)
* Deterministic Git fetch
* Temporary working directory

---

### 7.3 Source Fetching

**Implementation:**

* Primary: `git clone --depth 1 --branch <ref>` (for branches/tags)
* Fallback: `git clone --depth 1 --no-single-branch` + `git fetch` + `git checkout` (for commit SHAs)
* Uses temporary directories that are automatically cleaned up

**Rationale:**

* Supports directories and multiple files
* Handles private repos via existing Git credentials
* Robust handling of branches, tags, and commit SHAs

**Future enhancement:**

* Raw file fetching via HTTPS for single-file use cases

---

## 8. Safety & Guardrails

### Default Safety Guarantees

* ✔ Check-only by default
* ✔ Explicit opt-in via config file
* ✔ Explicit overwrite via `--write`
* ✔ Deterministic source reference
* ✔ No filename-based execution

### Failure Modes

| Scenario            | Behavior          |
| ------------------- | ----------------- |
| Missing config      | No-op             |
| Missing source file | Fail with message |
| Hash mismatch       | Fail (check mode) |
| Git clone failure   | Fail              |

---

## 9. CI Integration

Recommended usage in CI:

```bash
pre-commit run sync-common-files --all-files
```

This enforces drift detection without mutating files.

---

## 10. Versioning & Release Strategy

* Semantic versioning
* Immutable Git tags (required by pre-commit)
* Backwards-incompatible config changes require major version bump

---

## 11. Implementation Status

### ✅ Phase 1 (MVP) - **COMPLETE**

All MVP features have been implemented:

* ✅ **Single source repo** - Implemented with git clone support
* ✅ **Hash-based comparison** - SHA-256 hash comparison implemented
* ✅ **Check / write modes** - Both modes fully functional
* ✅ **CLI interface** - `sync-common-files [--write]` command implemented
* ✅ **pre-commit hook** - Hook definition in `.pre-commit-hooks.yaml`
* ✅ **Configuration loading** - TOML config parsing with validation
* ✅ **Source fetching** - Git clone with support for branches, tags, and commit SHAs
* ✅ **Error handling** - Comprehensive error handling with clear messages
* ✅ **Zero dependencies** - Uses only Python standard library (Python 3.11+)

### Implementation Details

**Core Components Implemented:**

1. **`cli.py`** - CLI entrypoint that:
   * Parses `--write` flag
   * Loads configuration
   * Invokes sync engine
   * Returns appropriate exit codes
   * Handles all error cases gracefully

2. **`sync.py`** - Sync engine that:
   * Loads and validates `.sync-files.toml` configuration
   * Searches for config in current and parent directories
   * Fetches source repository using git clone
   * Supports branches, tags, and commit SHAs
   * Compares files using SHA-256 hashes
   * Syncs files in write mode
   * Provides detailed error messages

3. **Configuration Format:**
   * TOML-based (using built-in `tomllib`)
   * Validates all required fields
   * Supports default mode configuration
   * Clear error messages for invalid configs

**Key Features:**

* ✅ Config file search in parent directories
* ✅ Robust git clone with fallback for commit SHAs
* ✅ Temporary directory management for source repos
* ✅ Parent directory creation for destination files
* ✅ Comprehensive error handling and user feedback

### Phase 2 - **PLANNED**

* Multiple sources
* Per-file policies
* Raw file fetch (no clone)

### Phase 3 - **PLANNED**

* Optional templating (Jinja2)
* Caching of source repo
* Pre-push support

---

## 12. Alternatives Considered

| Approach       | Why Not                    |
| -------------- | -------------------------- |
| Git submodules | Heavyweight, poor DX       |
| Monorepo       | Organizationally expensive |
| Copy-paste     | Error-prone, untraceable   |
| CI-only sync   | Too late in feedback loop  |

---

## 13. Open Questions

* Should templating be first-class or opt-in?
* Should writes be blocked in CI by default?
* Should repo refs be pinned to tags only?

## 14. Implementation Notes

### Technical Decisions

1. **TOML over YAML**: Changed from YAML to TOML to eliminate external dependencies (`tomllib` is built-in in Python 3.11+)
2. **Python 3.11+ requirement**: Enables use of built-in `tomllib`, ensuring zero external dependencies
3. **SHA-256 hashing**: Provides deterministic, fast file comparison
4. **Temporary directories**: Source repos are cloned to temp directories and automatically cleaned up
5. **Parent directory search**: Config file search traverses up the directory tree for flexibility

### Code Structure

```
precommit_sync_files/
├── __init__.py      # Package initialization
├── cli.py           # CLI entrypoint (78 lines)
└── sync.py          # Core sync engine (345 lines)
```

**Total implementation**: ~423 lines of Python code

---

## 15. Summary

**precommit-sync-files** provides a disciplined, low-friction mechanism for enforcing consistency across distributed repositories while preserving autonomy.

It is intentionally boring, predictable, and safe — qualities that make it suitable as infrastructure glue across fast-moving engineering teams.
