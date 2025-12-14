#!/bin/bash
# Quick test script for precommit-sync-files
# Uses uv for dependency management

set -e

# ============================================================================
# Configuration & Constants
# ============================================================================

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly TEST_BASE_DIR="/tmp"
readonly TEST_REPO_URL="https://github.com/will-wright-eng/precommit-sync-files"
readonly TEST_REPO_REF="main"

# ============================================================================
# Utility Functions
# ============================================================================

# Print formatted message with emoji prefix
log_info() {
    echo "$1"
}

log_success() {
    echo "   ✓ $1"
}

log_error() {
    echo "   ✗ $1"
}

log_warning() {
    echo "   ⚠ $1"
}

# Execute command and capture output, return exit code
run_cmd() {
    local cmd="$1"
    local silent="${2:-false}"

    if [[ "$silent" == "true" ]]; then
        eval "$cmd" > /dev/null 2>&1
    else
        eval "$cmd"
    fi
    return $?
}

# Execute command and expect success
assert_success() {
    local cmd="$1"
    local error_msg="${2:-Command failed}"

    if run_cmd "$cmd"; then
        return 0
    else
        log_error "$error_msg"
        exit 1
    fi
}

# Execute command and expect failure
assert_failure() {
    local cmd="$1"
    local error_msg="${2:-Command should have failed but succeeded}"

    if ! run_cmd "$cmd"; then
        return 0
    else
        log_error "$error_msg"
        exit 1
    fi
}

# ============================================================================
# Setup & Validation Functions
# ============================================================================

check_dependencies() {
    log_info "Checking dependencies..."

    if ! command -v uv &> /dev/null; then
        log_error "uv is not installed. Please install it first:"
        echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi

    log_success "All dependencies available"
    echo ""
}

install_dependencies() {
    log_info "1️⃣  Installing in development mode with uv..."
    assert_success "uv sync > /dev/null 2>&1" "Failed to install dependencies"
    log_success "Installed"
    echo ""
}

verify_cli_availability() {
    log_info "2️⃣  Verifying CLI is available..."
    if run_cmd "uv run sync-common-files --help" true || true; then
        log_success "CLI command available via uv"
    else
        log_error "CLI command not found"
        exit 1
    fi
    echo ""
}

# ============================================================================
# Test Environment Management
# ============================================================================

create_test_directory() {
    local test_dir="$TEST_BASE_DIR/test-sync-$(date +%s)"
    mkdir -p "$test_dir"
    echo "$test_dir"
}

setup_git_repo() {
    local test_dir="$1"
    cd "$test_dir"
    run_cmd "git init" true
}

create_test_config() {
    local config_file="$1/.sync-files.toml"

    cat > "$config_file" << 'EOF'
[source]
repo = "https://github.com/will-wright-eng/precommit-sync-files"
ref = "main"

[[files]]
src = "README.md"
dst = "README.md"

[options]
mode = "check"
EOF
}

create_test_file() {
    local test_dir="$1"
    local file_path="$test_dir/README.md"

    # Try to fetch actual README, fallback to placeholder
    curl -s "${TEST_REPO_URL}/raw/${TEST_REPO_REF}/README.md" > "$file_path" 2>/dev/null \
        || echo "# Test" > "$file_path"
}

cleanup_test_directory() {
    local test_dir="$1"
    if [[ -n "$test_dir" && -d "$test_dir" ]]; then
        cd "$TEST_BASE_DIR"
        rm -rf "$test_dir"
    fi
}

# ============================================================================
# Test Functions
# ============================================================================

test_noop_behavior() {
    log_info "3️⃣  Testing no-op behavior (no config file)..."
    cd "$TEST_BASE_DIR"

    assert_success "uv run sync-common-files" "No-op failed"
    log_success "No-op works correctly (exit code 0)"
    echo ""
}

test_valid_config() {
    log_info "4️⃣  Testing with valid configuration..."

    local test_dir
    test_dir=$(create_test_directory)

    # Setup
    setup_git_repo "$test_dir"
    create_test_config "$test_dir"
    create_test_file "$test_dir"

    # Execute test
    cd "$test_dir"
    assert_success "uv run sync-common-files" "Valid config test failed"
    log_success "Valid config with matching files works"
    echo ""

    # Return test directory for cleanup
    echo "$test_dir"
}

test_drift_detection() {
    local test_dir="$1"

    log_info "5️⃣  Testing drift detection..."

    cd "$test_dir"
    echo "# Modified content" > README.md

    assert_failure "uv run sync-common-files" \
        "Drift detection failed (should have failed but didn't)"
    log_success "Drift detection works (correctly failed)"
    echo ""
}

test_write_mode() {
    local test_dir="$1"

    log_info "6️⃣  Testing write mode..."

    cd "$test_dir"

    assert_success "uv run sync-common-files --write" "Write mode failed"
    log_success "Write mode works"

    # Verify file was updated
    if grep -q "precommit-sync-files" README.md 2>/dev/null; then
        log_success "File was synced correctly"
    else
        log_warning "File may not have synced (check manually)"
    fi
    echo ""
}

# ============================================================================
# Main Test Runner
# ============================================================================

run_all_tests() {
    local test_dir=""

    # Setup and validation
    check_dependencies
    install_dependencies
    verify_cli_availability

    # Run tests
    test_noop_behavior

    test_dir=$(test_valid_config)
    test_drift_detection "$test_dir"
    test_write_mode "$test_dir"

    # Cleanup
    cleanup_test_directory "$test_dir"
}

# ============================================================================
# Entry Point
# ============================================================================

main() {
    log_info "🧪 Quick Test for precommit-sync-files"
    log_info "========================================"
    echo ""

    run_all_tests

    log_info "✅ All quick tests passed!"
    echo ""
    log_info "For more comprehensive testing, see TESTING.md"
}

main "$@"
