#!/bin/bash -e

ktfmt --kotlinlang-style android_app/*.{kt,kts} android_app/{app,build-logic} android_app/library/{network,utils}
black app/ scripts/
npx prettier --write evaluation/
