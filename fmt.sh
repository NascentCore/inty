#！/bin/bash -e
#检查--全部标志
FORMAT_ALL=false
if [ "$1" = "--all" ]; then
    FORMAT_ALL=true
fi

if [ "$FORMAT_ALL" = true ]; then
    echo "Formatting all files..."
# 格式化所有 Kotlin 文件
    ktfmt --kotlinlang-style android_app/
# 格式化所有Python文件
    black app/ scripts/ experimental/
# 格式化所有其他文件
    npx prettier --write evaluation/
    echo "Formatting complete!"
    echo
    
    git commit --all --message "fmt all code: ktfmt black prettier"
    echo "Committing complete!"
    echo
    exit 0
fi
# 获取与主分支相比已更改的文件列表
CHANGED_FILES=$(git diff --name-only main)

if [ -z "$CHANGED_FILES" ]; then
    echo "No files changed compared to main branch"
    exit 0
fi
# 按类型收集文件
KOTLIN_FILES=""
PYTHON_FILES=""
OTHER_FILES=""

for file in $CHANGED_FILES; do
    case "$file" in
        *.kt|*.kts)
            KOTLIN_FILES="$KOTLIN_FILES $file"
            ;;
        *.py)
            PYTHON_FILES="$PYTHON_FILES $file"
            ;;
        *.json|*.md|*.js|*.ts|*.tsx|*.css|*.html|*.yaml|*.yml)
            OTHER_FILES="$OTHER_FILES $file"
            ;;
    esac
done
# 设置 Kotlin 文件格式
if [ -n "$KOTLIN_FILES" ]; then
    echo "Formatting Kotlin files with ktfmt..."
    ktfmt --kotlinlang-style $KOTLIN_FILES
fi
# 格式化Python文件
if [ -n "$PYTHON_FILES" ]; then
    echo "Formatting Python files with black..."
    black $PYTHON_FILES
fi
# 使用 prettier 格式化其他文件
if [ -n "$OTHER_FILES" ]; then
    echo "Formatting other files with prettier..."
    npx prettier --write $OTHER_FILES
fi

echo "Formatting complete!"
echo

git commit --all --message "fmt changed files: ktfmt black prettier"
echo "Committing complete!"
echo
