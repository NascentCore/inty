#!/bin/bash -ex

INTY_SDK_PYTHON_DIR=sdks/python
pushd $INTY_SDK_PYTHON_DIR
git checkout main
git pull
popd
git add $INTY_SDK_PYTHON_DIR
git commit -m "更新 $INTY_SDK_PYTHON_DIR submodule"

INTY_SDK_KOTLIN_DIR=android_app/library/inty_sdk
pushd $INTY_SDK_KOTLIN_DIR
git checkout main
git pull
popd
git add $INTY_SDK_KOTLIN_DIR
git commit -m "更新 $INTY_SDK_KOTLIN_DIR submodule"

INTY_SDK_TYPESCRIPT_DIR=sdks/typescript
pushd $INTY_SDK_TYPESCRIPT_DIR
git checkout main
git pull
popd
git add $INTY_SDK_TYPESCRIPT_DIR
git commit -m "更新 $INTY_SDK_TYPESCRIPT_DIR submodule"