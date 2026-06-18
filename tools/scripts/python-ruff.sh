# Shared ruff helpers for git hooks.
# Scope: app/ backend/ tests/ (same paths as python-black.sh). Rule: F401 unused imports only.

RUFF_UNUSED_IMPORT_RULE="F401"

run_ruff_fix_unused_imports() {
    if [ "$#" -eq 0 ]; then
        return 0
    fi
    echo "Removing unused imports with uv run ruff check --select ${RUFF_UNUSED_IMPORT_RULE} --fix..."
    uv run ruff check --select "${RUFF_UNUSED_IMPORT_RULE}" --fix "$@"
}
