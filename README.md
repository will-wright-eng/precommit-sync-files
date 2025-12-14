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
```

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

## Usage

### Pre-commit (automatic)

The hook runs automatically on `git commit` when configured. It will:

1. Check if `.sync-files.toml` exists (no-op if missing)
2. Fetch the source repository at the specified ref
3. Compare files using SHA-256 hashes
4. Fail if drift is detected (in `check` mode)
5. Auto-sync files if `--write` flag is used

### Manual execution

```bash
# Check mode (default)
sync-common-files

# Write mode (auto-sync files)
sync-common-files --write
```

### CI Integration

Recommended usage in CI:

```bash
pre-commit run sync-common-files --all-files
```

This enforces drift detection without mutating files.

## How It Works

1. **Configuration Loading**: Reads `.sync-files.toml` from repository root
2. **Source Fetching**: Clones source repository using `git clone --depth 1`
3. **File Comparison**: Computes SHA-256 hashes for each file pair
4. **Drift Detection**: Reports mismatches or auto-syncs based on mode

## Requirements

- Python 3.11+ (uses built-in `tomllib` module)
- Git (for cloning source repositories)

## Safety Guarantees

- ✔ Check-only by default
- ✔ Explicit opt-in via config file
- ✔ Explicit overwrite via `--write` flag
- ✔ Deterministic source reference
- ✔ No silent overwrites

## Failure Modes

| Scenario            | Behavior          |
| ------------------- | ----------------- |
| Missing config      | No-op (passes)    |
| Missing source file | Fail with message |
| Hash mismatch       | Fail (check mode) |
| Git clone failure   | Fail              |

## Development

### Setup

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

```bash
# Clone the repository
git clone https://github.com/will-wright-eng/precommit-sync-files
cd precommit-sync-files

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install in development mode
uv sync

# Run the CLI
uv run sync-common-files

# Or activate the virtual environment
source .venv/bin/activate  # On Unix/Mac
sync-common-files
```

### Running Tests

```bash
# Run the quick test script
./test_quick.sh

# Or run tests manually (see TESTING.md for details)
uv run sync-common-files
```

### Project Structure

```
precommit-sync-files/
├── precommit_sync_files/
│   ├── __init__.py
│   ├── cli.py          # CLI entrypoint
│   └── sync.py         # Core sync engine
├── .pre-commit-hooks.yaml
├── pyproject.toml
├── test_quick.sh       # Quick test script
├── TESTING.md          # Comprehensive testing guide
└── README.md
```

## License

MIT License

## Contributing

Contributions welcome! Please open an issue or submit a pull request.
