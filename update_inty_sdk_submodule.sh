#!/bin/bash -ex

INTY_SDK_KOTLIN_DIR=android_app/library/inty_sdk
mkdir -p $INTY_SDK_KOTLIN_DIR
pushd $INTY_SDK_KOTLIN_DIR
git checkout main
git pull
popd
# commit if there are changes
if [ -n "$(git status --porcelain)" ]; then
    git add $INTY_SDK_KOTLIN_DIR
    git commit -m "更新 $INTY_SDK_KOTLIN_DIR submodule"
fi

INTY_SDK_TYPESCRIPT_DIR=evaluation/inty_sdk
mkdir -p $INTY_SDK_TYPESCRIPT_DIR
pushd $INTY_SDK_TYPESCRIPT_DIR
git checkout main
git pull
popd
# commit if there are changes
if [ -n "$(git status --porcelain)" ]; then
    git add $INTY_SDK_TYPESCRIPT_DIR
    git commit -m "更新 $INTY_SDK_TYPESCRIPT_DIR submodule"
fi
