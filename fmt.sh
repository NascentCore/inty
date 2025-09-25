#!/bin/bash -e

ktfmt --kotlinlang-style android_app/*.{kt,kts} android_app/{app,build-logic} android_app/library/{network,utils}
black app/ scripts/
# 格式化包括 json md 等等
npx prettier --write .
