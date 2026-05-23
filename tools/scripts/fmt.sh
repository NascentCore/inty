#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

# Python 格式化范围与 .agents/guidelines/py-style-tooling.md 一致；配置见 pyproject.toml [tool.black]（80 列）。
PYTHON_FORMAT_PATHS=(app backend)

# 与 tools/scripts/lint-markdown.sh 使用同一 CLI；本地若无 node_modules 则自动 npm install。
run_markdownlint() {
    echo "Linting Markdown (markdownlint-cli2)..."
    if [ ! -d tools/markdownlint/node_modules ]; then
        npm install --prefix tools/markdownlint
    fi
    npx --prefix tools/markdownlint markdownlint-cli2
}

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

# Check for --all flag and CI commit behavior
FORMAT_ALL=false
FMT_NO_COMMIT=${FMT_NO_COMMIT:-false}
if [ "${1:-}" = "--all" ]; then
    FORMAT_ALL=true
fi

if [ "$FORMAT_ALL" = true ]; then
    echo "Formatting all files..."
    # Format all Kotlin files
    ktfmt --kotlinlang-style android_app/
    # Format all Python files
    run_black "${PYTHON_FORMAT_PATHS[@]}"
    # Format all other files
    npx prettier --write evaluation/ web_app/
    run_markdownlint
    echo "Formatting complete!"
    echo

    if [ "$FMT_NO_COMMIT" = true ]; then
        echo "Skipping commit in CI (FMT_NO_COMMIT=true)."
    else
        if git diff --quiet; then
            echo "No formatting changes to commit."
        else
            git commit --all --message "fmt all code: ktfmt uv run black prettier"
            echo "Committing complete!"
        fi
    fi
    echo
    exit 0
fi

# Get list of files changed compared to main branch
CHANGED_FILES=$(git diff --name-only main)

if [ -z "$CHANGED_FILES" ]; then
    echo "No files changed compared to main branch"
    exit 0
fi

# Collect files by type
KOTLIN_FILES=""
PYTHON_FILES=""
OTHER_FILES=""

for file in $CHANGED_FILES; do
    case "$file" in
        *.kt|*.kts)
            KOTLIN_FILES="$KOTLIN_FILES $file"
            ;;
        *.py)
            if is_python_format_path "$file"; then
                PYTHON_FILES="$PYTHON_FILES $file"
            fi
            ;;
        *.json|*.md|*.js|*.ts|*.tsx|*.css|*.html|*.yaml|*.yml)
            OTHER_FILES="$OTHER_FILES $file"
            ;;
    esac
done

# Format Kotlin files
if [ -n "$KOTLIN_FILES" ]; then
    echo "Formatting Kotlin files with ktfmt..."
    ktfmt --kotlinlang-style $KOTLIN_FILES
fi

run_black $PYTHON_FILES

# Format other files with prettier
if [ -n "$OTHER_FILES" ]; then
    echo "Formatting other files with prettier..."
    npx prettier --write $OTHER_FILES
fi

run_markdownlint

echo "Formatting complete!"
echo

if [ "$FMT_NO_COMMIT" = true ]; then
    echo "Skipping commit in CI (FMT_NO_COMMIT=true)."
else
    if git diff --quiet; then
        echo "No formatting changes to commit."
    else
        git commit --all --message "fmt changed files: ktfmt uv run black prettier"
        echo "Committing complete!"
    fi
fi
echo
