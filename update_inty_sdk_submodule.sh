#！/bin/bash -ex

INTY_SDK_KOTLIN_DIR=android_app/library/inty_sdk
pushd $INTY_SDK_KOTLIN_DIR
git checkout main
git pull
popd
# 如果有变化则提交
if [ -n "$(git status --porcelain)" ]; then
    git add $INTY_SDK_KOTLIN_DIR
    git commit -m "更新 $INTY_SDK_KOTLIN_DIR submodule"
fi

INTY_SDK_TYPESCRIPT_DIR=evaluation/inty_sdk
pushd $INTY_SDK_TYPESCRIPT_DIR
git checkout main
git pull
popd
# 如果有变化则提交
if [ -n "$(git status --porcelain)" ]; then
    git add $INTY_SDK_TYPESCRIPT_DIR
    git commit -m "更新 $INTY_SDK_TYPESCRIPT_DIR submodule"
fi
