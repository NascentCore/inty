#!/bin/bash -e

ktfmt --kotlinlang-style android_app/app/src
black app/ scripts/
npx prettier --write evaluation/