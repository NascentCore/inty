# Shared Python black helpers for fmt.sh and git hooks.
# Config: pyproject.toml [tool.black] (80 cols). Scope: app/ backend/.

PYTHON_FORMAT_PATHS=(app backend)

is_python_format_path() {
    local file="$1"
    local dir
    for dir in "${PYTHON_FORMAT_PATHS[@]}"; do
        if [[ "$file" == "${dir}/"* ]]; then
            return 0
        fi
    done
    return 1
}

run_black() {
    if [ "$#" -eq 0 ]; then
        return 0
    fi
    echo "Formatting Python files with uv run black..."
    uv run black "$@"
}
