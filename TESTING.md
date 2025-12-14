# Testing Guide

This guide explains how to test `precommit-sync-files` both as a standalone tool and as a pre-commit hook.

## Prerequisites

- [uv](https://github.com/astral-sh/uv) installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Python 3.11 or higher (uv will manage this)
- Git installed
- The repository cloned locally

## Step 1: Install in Development Mode

```bash
# From the repository root
uv sync
```

This installs the package and its dependencies in a virtual environment managed by uv.

Verify installation:

```bash
# Run the command via uv
uv run sync-common-files

# Or activate the environment and run directly
source .venv/bin/activate  # On Unix/Mac
sync-common-files --help
```

## Step 2: Test Without Configuration (No-op)

The hook should be a no-op when no config file exists:

```bash
# From any directory without .sync-files.toml
uv run sync-common-files
echo $?  # Should output 0 (success, no-op)
```

## Step 3: Test with a Real Configuration

### Option A: Test Against This Repository

Create a test config that syncs files from this repo to itself:

```bash
# Create a test config
cat > .sync-files.toml << 'EOF'
[source]
repo = "https://github.com/will-wright-eng/precommit-sync-files"
ref = "main"

[[files]]
src = "README.md"
dst = "README.md"

[[files]]
src = "pyproject.toml"
dst = "pyproject.toml"

[options]
mode = "check"
EOF
```

Test check mode (should pass if files match):

```bash
uv run sync-common-files
echo $?  # Should be 0 if files match
```

### Option B: Test with File Drift

1. Create a test directory:

```bash
mkdir -p /tmp/test-sync-repo
cd /tmp/test-sync-repo
git init
```

1. Create a config that syncs from this repo:

```bash
cat > .sync-files.toml << 'EOF'
[source]
repo = "https://github.com/will-wright-eng/precommit-sync-files"
ref = "main"

[[files]]
src = "README.md"
dst = "README.md"

[options]
mode = "check"
EOF
```

1. Create a README.md that differs from the source:

```bash
echo "# Different Content" > README.md
```

1. Test check mode (should fail):

```bash
uv run sync-common-files
echo $?  # Should be 1 (failure due to drift)
```

1. Test write mode (should sync):

```bash
uv run sync-common-files --write
echo $?  # Should be 0 (success)
cat README.md  # Should now match the source
```

## Step 4: Test as a Pre-commit Hook

### Setup

1. Create a test repository:

```bash
mkdir -p /tmp/test-precommit-repo
cd /tmp/test-precommit-repo
git init
```

1. Install pre-commit (if not already installed):

```bash
uv pip install pre-commit
# Or add it to dev-dependencies in pyproject.toml and run: uv sync
```

1. Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: sync-common-files
        name: Sync common files across repos
        entry: sync-common-files
        language: system
        pass_filenames: false
```

Or test with the local repo:

```yaml
repos:
  - repo: /Users/will/repos/precommit-sync-files
    hooks:
      - id: sync-common-files
```

1. Create `.sync-files.toml`:

```toml
[source]
repo = "https://github.com/will-wright-eng/precommit-sync-files"
ref = "main"

[[files]]
src = "README.md"
dst = "README.md"

[options]
mode = "check"
```

1. Install the hook:

```bash
pre-commit install
```

1. Test the hook:

```bash
# Create a file that will trigger the hook
echo "test" > test.txt
git add test.txt

# Try to commit (hook will run)
git commit -m "Test commit"
# If README.md doesn't match, commit will fail
```

## Step 5: Test Error Cases

### Invalid Configuration

```bash
# Create invalid TOML
echo "invalid toml content" > .sync-files.toml
uv run sync-common-files
# Should show configuration error
```

### Missing Source File

```bash
cat > .sync-files.toml << 'EOF'
[source]
repo = "https://github.com/will-wright-eng/precommit-sync-files"
ref = "main"

[[files]]
src = "nonexistent-file.txt"
dst = "nonexistent-file.txt"

[options]
mode = "check"
EOF

uv run sync-common-files
# Should show error about missing source file
```

### Invalid Repository

```bash
cat > .sync-files.toml << 'EOF'
[source]
repo = "https://github.com/invalid/repo-that-does-not-exist"
ref = "main"

[[files]]
src = "README.md"
dst = "README.md"

[options]
mode = "check"
EOF

uv run sync-common-files
# Should show error about git clone failure
```

## Step 6: Test with Different Ref Types

### Test with a Tag

```toml
[source]
repo = "https://github.com/will-wright-eng/precommit-sync-files"
ref = "v0.1.0"  # If you have tags
```

### Test with a Commit SHA

```toml
[source]
repo = "https://github.com/will-wright-eng/precommit-sync-files"
ref = "abc123def456..."  # Use an actual commit SHA
```

## Quick Test Script

A quick test script is provided: `./test_quick.sh`

```bash
# Make it executable (if needed)
chmod +x test_quick.sh

# Run it
./test_quick.sh
```

Or run tests manually with uv:

```bash
#!/bin/bash
set -e

echo "Testing precommit-sync-files..."

# Test 1: No config (should be no-op)
echo "Test 1: No config file"
cd /tmp
uv run sync-common-files || echo "  ✓ No-op works"

# Test 2: Valid config with matching files
echo "Test 2: Valid config with matching files"
cd /tmp
mkdir -p test-sync-valid
cd test-sync-valid
git init
cat > .sync-files.toml << 'EOF'
[source]
repo = "https://github.com/will-wright-eng/precommit-sync-files"
ref = "main"

[[files]]
src = "README.md"
dst = "README.md"

[options]
mode = "check"
EOF
# Copy README from source to test
curl -s https://raw.githubusercontent.com/will-wright-eng/precommit-sync-files/main/README.md > README.md
uv run sync-common-files && echo "  ✓ Matching files work"

# Test 3: Drift detection
echo "Test 3: Drift detection"
echo "# Modified" > README.md
uv run sync-common-files && echo "  ✗ Should have failed" || echo "  ✓ Drift detection works"

# Test 4: Write mode
echo "Test 4: Write mode"
uv run sync-common-files --write && echo "  ✓ Write mode works"

echo "All tests complete!"
```

## Manual Testing Checklist

- [ ] Install package in development mode
- [ ] Test no-op behavior (no config file)
- [ ] Test with valid config and matching files
- [ ] Test drift detection (files differ)
- [ ] Test write mode (auto-sync)
- [ ] Test invalid configuration
- [ ] Test missing source file
- [ ] Test invalid repository URL
- [ ] Test with branch ref
- [ ] Test with tag ref
- [ ] Test with commit SHA ref
- [ ] Test as pre-commit hook
- [ ] Test error messages are clear

## Debugging

If something doesn't work:

1. **Check uv is installed**: `uv --version`
2. **Check Python version**: `uv python list` or `python3 --version` (must be 3.11+)
3. **Check installation**: `uv pip list | grep precommit-sync-files` or check `.venv/`
4. **Run with verbose output**: The CLI prints errors to stderr
5. **Check git is available**: `git --version`
6. **Test config parsing**: Try loading the config manually with Python:

   ```bash
   uv run python -c "import tomllib; f = open('.sync-files.toml', 'rb'); print(tomllib.load(f))"
   ```

## Next Steps

Once basic testing passes, consider:

- Adding unit tests with pytest
- Testing with private repositories
- Testing with large files
- Testing with multiple file mappings
- Performance testing with many files
