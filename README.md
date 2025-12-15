# precommit-sync-files

A reusable [pre-commit](https://pre-commit.com) hook that ensures a set of common, canonical files remain synchronized across multiple Git repositories.

## Features

- ✅ **Check-only by default** - Detects drift without modifying files
- ✅ **Opt-in configuration** - Only runs when `.sync-files.toml` is present
- ✅ **Safe and deterministic** - Uses SHA-256 hashes for comparison
- ✅ **CI-friendly** - Perfect for enforcing consistency in CI pipelines
- ✅ **Simple TOML configuration** - Easy to set up and maintain
- ✅ **Zero external dependencies** - Uses only Python standard library

## Installation

### As a pre-commit hook

Add this to your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/will-wright-eng/precommit-sync-files
    rev: v0.1.0  # Use the tag you want
    hooks:
      - id: sync-common-files
        # Optional: add --write to automatically sync files
        # args: [--write,--debug]
```

**Hook Arguments:**

- No arguments (default): Check mode - detects drift without modifying files
- `args: [--write]`: Write mode - automatically syncs files that differ
- `args: [--debug]`: Debug mode - print verbose output

Then run:

```bash
pre-commit install
```

### Standalone installation

```bash
pip install precommit-sync-files
```

Or with `uv`:

```bash
uv pip install precommit-sync-files
```

## Configuration

Create a `.sync-files.toml` file in your repository root:

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

### Configuration Fields

| Field          | Description                               |
| -------------- | ----------------------------------------- |
| `source.repo`  | Git repository containing canonical files |
| `source.ref`   | Branch, tag, or commit SHA                |
| `files[].src`  | Path inside source repo                   |
| `files[].dst`  | Path inside consuming repo                |
| `options.mode` | Default execution mode (`check` or `write`) |
